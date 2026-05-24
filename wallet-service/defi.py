"""
Aerodrome (Base) DeFi action builders for the Sovereignty Stack wallet.

Everything here is *pure*: it constructs the `data` (calldata) hex and names the
target contract for a transaction. No signing, no broadcasting, no FastAPI, no
app state. The wallet's existing estimate -> simulate -> send pipeline does the
actual signing/broadcasting, so every DeFi action still passes through the same
review + simulation gate as a plain transfer.

All ABI encoding goes through eth_abi (a dependency of eth-account, already in
requirements). We never hand-roll struct/array encoding.

Addresses + signatures verified against the official deployment:
  https://github.com/aerodrome-finance/contracts  (README deployment table,
  interfaces/IRouter.sol, IVoter.sol, IVotingEscrow.sol, IRewardsDistributor.sol)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from eth_abi import decode as abi_decode
from eth_abi import encode as abi_encode
from eth_utils import keccak, to_checksum_address


# ============================================================================
# Selectors
# ============================================================================
def _sel(sig: str) -> str:
    return "0x" + keccak(sig.encode()).hex()[:8]


SELECTORS = {
    # Router
    "swapExactTokensForTokens": _sel(
        "swapExactTokensForTokens(uint256,uint256,(address,address,bool,address)[],address,uint256)"),
    "swapExactETHForTokens": _sel(
        "swapExactETHForTokens(uint256,(address,address,bool,address)[],address,uint256)"),
    "swapExactTokensForETH": _sel(
        "swapExactTokensForETH(uint256,uint256,(address,address,bool,address)[],address,uint256)"),
    "getAmountsOut": _sel("getAmountsOut(uint256,(address,address,bool,address)[])"),
    # VotingEscrow
    "createLock": _sel("createLock(uint256,uint256)"),
    "increaseAmount": _sel("increaseAmount(uint256,uint256)"),
    "increaseUnlockTime": _sel("increaseUnlockTime(uint256,uint256)"),
    "withdraw": _sel("withdraw(uint256)"),
    "locked": _sel("locked(uint256)"),
    "balanceOf": _sel("balanceOf(address)"),
    "ownerToNFTokenIdList": _sel("ownerToNFTokenIdList(address,uint256)"),
    # Voter
    "vote": _sel("vote(uint256,address[],uint256[])"),
    "reset": _sel("reset(uint256)"),
    "claimRewards": _sel("claimRewards(address[])"),
    "claimBribes": _sel("claimBribes(address[],address[][],uint256)"),
    "claimFees": _sel("claimFees(address[],address[][],uint256)"),
    "gauges": _sel("gauges(address)"),
    "gaugeToFees": _sel("gaugeToFees(address)"),
    "gaugeToBribe": _sel("gaugeToBribe(address)"),
    "isPool": _sel("isPool(address)"),
    # RewardsDistributor
    "rd_claim": _sel("claim(uint256)"),
    "rd_claimable": _sel("claimable(uint256)"),
    # ERC20 / Pool / Reward views
    "approve": _sel("approve(address,uint256)"),
    "allowance": _sel("allowance(address,address)"),
    "token0": _sel("token0()"),
    "token1": _sel("token1()"),
    "rewardsListLength": _sel("rewardsListLength()"),
    "rewards": _sel("rewards(uint256)"),
    "decimals": _sel("decimals()"),
    "symbol": _sel("symbol()"),
    # Sugar
    "epochsLatest": _sel("epochsLatest(uint256,uint256)"),
}

# ABI return type for RewardsSugar.epochsLatest:
#   LpEpoch[] where LpEpoch =
#     (uint256 ts, address lp, uint256 votes, uint256 emissions,
#      LpEpochReward[] bribes, LpEpochReward[] fees)
#   and LpEpochReward = (address token, uint256 amount)
_EPOCHS_RETURN_TYPE = (
    "(uint256,address,uint256,uint256,(address,uint256)[],(address,uint256)[])[]"
)


# ============================================================================
# Aerodrome deployment registry (Base mainnet only)
# ============================================================================
AERODROME: Dict[int, Dict[str, str]] = {
    8453: {
        "router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
        "voter": "0x16613524e02ad97eDfeF371bC883F2F5d6C480A5",
        "voting_escrow": "0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4",
        "rewards_distributor": "0x227f65131A261548b057215bB1D5Ab2997964C7d",
        "pool_factory": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
        "aero": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
        "weth": "0x4200000000000000000000000000000000000006",
        # Sugar: Aerodrome's on-chain read API (velodrome-finance/sugar).
        "rewards_sugar": "0x1b121EfDaF4ABb8785a315C51D29BCE0552A7678",
    },
}

# Sentinel address the UI uses to mean "native ETH" (not a real contract).
NATIVE = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

# Curated swap tokens for Base. The UI shows these in a dropdown; users can also
# paste any custom token address (routing handles both identically).
SWAP_TOKENS: Dict[int, List[Dict[str, Any]]] = {
    8453: [
        {"symbol": "ETH", "address": NATIVE, "decimals": 18, "native": True},
        {"symbol": "WETH", "address": "0x4200000000000000000000000000000000000006", "decimals": 18},
        {"symbol": "USDC", "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6},
        {"symbol": "AERO", "address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "decimals": 18},
        {"symbol": "cbETH", "address": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22", "decimals": 18},
    ],
}

# Max lock time is 4 years; durations round down to whole weeks on-chain.
WEEK = 7 * 24 * 3600
MAXTIME = 4 * 365 * 24 * 3600
MAX_UINT256 = 2**256 - 1


def aerodrome_for(chain_id: int) -> Dict[str, str]:
    d = AERODROME.get(chain_id)
    if not d:
        raise ValueError(f"Aerodrome is not configured for chain {chain_id}")
    return d


def _addr(a: str) -> str:
    """Normalize to a checksummed address; raises on malformed input."""
    if not (isinstance(a, str) and a.startswith("0x") and len(a) == 42):
        raise ValueError(f"invalid address: {a!r}")
    return to_checksum_address(a)


def _data(selector: str, types: List[str], values: List[Any]) -> str:
    return selector + abi_encode(types, values).hex()


# A Route tuple is (from, to, stable, factory).
Route = Tuple[str, str, bool, str]


# ============================================================================
# Write builders -> calldata hex (target contract chosen by caller via the
# registry). Each returns a 0x-prefixed hex string.
# ============================================================================
def build_approve(spender: str, amount: int) -> str:
    return _data(SELECTORS["approve"], ["address", "uint256"], [_addr(spender), int(amount)])


def build_swap_exact_tokens_for_tokens(amount_in: int, amount_out_min: int,
                                       routes: List[Route], to: str, deadline: int) -> str:
    r = [(_addr(f), _addr(t), bool(s), _addr(fac)) for (f, t, s, fac) in routes]
    return _data(
        SELECTORS["swapExactTokensForTokens"],
        ["uint256", "uint256", "(address,address,bool,address)[]", "address", "uint256"],
        [int(amount_in), int(amount_out_min), r, _addr(to), int(deadline)],
    )


def build_swap_exact_eth_for_tokens(amount_out_min: int, routes: List[Route],
                                    to: str, deadline: int) -> str:
    r = [(_addr(f), _addr(t), bool(s), _addr(fac)) for (f, t, s, fac) in routes]
    return _data(
        SELECTORS["swapExactETHForTokens"],
        ["uint256", "(address,address,bool,address)[]", "address", "uint256"],
        [int(amount_out_min), r, _addr(to), int(deadline)],
    )


def build_swap_exact_tokens_for_eth(amount_in: int, amount_out_min: int,
                                    routes: List[Route], to: str, deadline: int) -> str:
    r = [(_addr(f), _addr(t), bool(s), _addr(fac)) for (f, t, s, fac) in routes]
    return _data(
        SELECTORS["swapExactTokensForETH"],
        ["uint256", "uint256", "(address,address,bool,address)[]", "address", "uint256"],
        [int(amount_in), int(amount_out_min), r, _addr(to), int(deadline)],
    )


def build_create_lock(value: int, lock_duration: int) -> str:
    return _data(SELECTORS["createLock"], ["uint256", "uint256"], [int(value), int(lock_duration)])


def build_increase_amount(token_id: int, value: int) -> str:
    return _data(SELECTORS["increaseAmount"], ["uint256", "uint256"], [int(token_id), int(value)])


def build_increase_unlock_time(token_id: int, lock_duration: int) -> str:
    return _data(SELECTORS["increaseUnlockTime"], ["uint256", "uint256"],
                 [int(token_id), int(lock_duration)])


def build_vote(token_id: int, pools: List[str], weights: List[int]) -> str:
    if len(pools) != len(weights):
        raise ValueError("pools and weights length mismatch")
    if not pools:
        raise ValueError("at least one pool required")
    return _data(
        SELECTORS["vote"], ["uint256", "address[]", "uint256[]"],
        [int(token_id), [_addr(p) for p in pools], [int(w) for w in weights]],
    )


def build_reset(token_id: int) -> str:
    return _data(SELECTORS["reset"], ["uint256"], [int(token_id)])


def build_rewards_distributor_claim(token_id: int) -> str:
    return _data(SELECTORS["rd_claim"], ["uint256"], [int(token_id)])


def build_claim_fees(fees: List[str], tokens: List[List[str]], token_id: int) -> str:
    return _data(
        SELECTORS["claimFees"], ["address[]", "address[][]", "uint256"],
        [[_addr(f) for f in fees], [[_addr(t) for t in grp] for grp in tokens], int(token_id)],
    )


def build_claim_bribes(bribes: List[str], tokens: List[List[str]], token_id: int) -> str:
    return _data(
        SELECTORS["claimBribes"], ["address[]", "address[][]", "uint256"],
        [[_addr(b) for b in bribes], [[_addr(t) for t in grp] for grp in tokens], int(token_id)],
    )


def build_claim_rewards(gauges: List[str]) -> str:
    return _data(SELECTORS["claimRewards"], ["address[]"], [[_addr(g) for g in gauges]])


# ============================================================================
# Read builders (eth_call data) + return decoders. The server runs these
# through rpc_call("eth_call", ...).
# ============================================================================
def read_allowance(owner: str, spender: str) -> str:
    return _data(SELECTORS["allowance"], ["address", "address"], [_addr(owner), _addr(spender)])


def read_balance_of(owner: str) -> str:
    return _data(SELECTORS["balanceOf"], ["address"], [_addr(owner)])


def read_owner_to_nftoken_id_list(owner: str, index: int) -> str:
    return _data(SELECTORS["ownerToNFTokenIdList"], ["address", "uint256"], [_addr(owner), int(index)])


def read_locked(token_id: int) -> str:
    return _data(SELECTORS["locked"], ["uint256"], [int(token_id)])


def read_rd_claimable(token_id: int) -> str:
    return _data(SELECTORS["rd_claimable"], ["uint256"], [int(token_id)])


def read_get_amounts_out(amount_in: int, routes: List[Route]) -> str:
    r = [(_addr(f), _addr(t), bool(s), _addr(fac)) for (f, t, s, fac) in routes]
    return _data(SELECTORS["getAmountsOut"], ["uint256", "(address,address,bool,address)[]"],
                 [int(amount_in), r])


def read_call(selector_name: str, types: List[str], values: List[Any]) -> str:
    return _data(SELECTORS[selector_name], types, values)


def read_epochs_latest(limit: int, offset: int) -> str:
    return _data(SELECTORS["epochsLatest"], ["uint256", "uint256"], [int(limit), int(offset)])


def decode_epochs_latest(result_hex: str) -> List[Dict[str, Any]]:
    """Decode RewardsSugar.epochsLatest -> list of per-pool epoch dicts."""
    rows = abi_decode([_EPOCHS_RETURN_TYPE], _strip(result_hex))[0]
    out: List[Dict[str, Any]] = []
    for (ts, lp, votes, emissions, bribes, fees) in rows:
        out.append({
            "ts": int(ts),
            "lp": to_checksum_address(lp),
            "votes": int(votes),
            "emissions": int(emissions),
            "bribes": [{"token": to_checksum_address(t), "amount": int(a)} for (t, a) in bribes],
            "fees": [{"token": to_checksum_address(t), "amount": int(a)} for (t, a) in fees],
        })
    return out


EPOCHS_PER_YEAR = 52  # weekly voting epochs


def rank_voting_pools(epochs: List[Dict[str, Any]],
                      decimals_of: Dict[str, int],
                      price_of: Dict[str, float],
                      aero_price: Optional[float],
                      top_n: int = 15) -> List[Dict[str, Any]]:
    """Pure ranking: given epoch data + (lowercased-address-keyed) decimals and
    USD prices, compute each pool's voting APR and return the best `top_n`.

    A pool's incentive $ for the epoch is the sum of its bribe + fee token
    amounts priced in USD. Voting APR ~= (incentive$ / votes$) * 52. Tokens we
    can't price are still listed (raw) but don't contribute to the $ total, so
    APR is a conservative lower bound. Falls back to ranking by votes when no
    USD prices are available at all."""
    results: List[Dict[str, Any]] = []
    for e in epochs:
        votes_raw = e["votes"]
        votes_aero = votes_raw / 1e18
        # Aggregate incentives by token (bribes + fees combined).
        agg: Dict[str, int] = {}
        for r in list(e["bribes"]) + list(e["fees"]):
            t = r["token"].lower()
            agg[t] = agg.get(t, 0) + int(r["amount"])
        if votes_raw == 0 and not agg:
            continue  # dead pool — skip

        incentives_usd = 0.0
        priced_complete = True
        breakdown: List[Dict[str, Any]] = []
        for t, raw in agg.items():
            dec = decimals_of.get(t)
            price = price_of.get(t)
            human = (raw / (10 ** dec)) if dec is not None else None
            usd = (human * price) if (human is not None and price is not None) else None
            if usd is None:
                priced_complete = False
            else:
                incentives_usd += usd
            breakdown.append({"token": t, "amount_raw": str(raw),
                              "amount": human, "usd": usd})

        votes_usd = (votes_aero * aero_price) if aero_price else None
        apr = None
        if votes_usd and votes_usd > 0 and incentives_usd > 0:
            apr = (incentives_usd / votes_usd) * EPOCHS_PER_YEAR * 100.0

        results.append({
            "pool": e["pool"] if "pool" in e else e["lp"],
            "votes_raw": str(votes_raw),
            "votes_aero": votes_aero,
            "incentives_usd": incentives_usd,
            "apr": apr,
            "priced_complete": priced_complete,
            "incentives": breakdown,
        })

    any_apr = any(r["apr"] is not None for r in results)
    if any_apr:
        # APR desc (None last), then incentive $ desc.
        results.sort(key=lambda r: (
            r["apr"] is not None, r["apr"] or 0.0, r["incentives_usd"]), reverse=True)
    else:
        # No prices: rank by raw votes desc, then incentive token count.
        results.sort(key=lambda r: (float(r["votes_raw"]), len(r["incentives"])), reverse=True)
    return results[:top_n]


def _strip(result_hex: str) -> bytes:
    return bytes.fromhex((result_hex or "0x").removeprefix("0x") or "")


def decode_uint(result_hex: str) -> int:
    b = _strip(result_hex)
    return int.from_bytes(b[-32:], "big") if b else 0


def decode_address(result_hex: str) -> str:
    b = _strip(result_hex)
    if len(b) < 32:
        return "0x" + "0" * 40
    return to_checksum_address("0x" + b[-20:].hex())


def decode_locked(result_hex: str) -> Dict[str, Any]:
    """locked() returns (int128 amount, uint256 end, bool isPermanent)."""
    amount, end, is_perm = abi_decode(["int128", "uint256", "bool"], _strip(result_hex))
    return {"amount": int(amount), "end": int(end), "is_permanent": bool(is_perm)}


def decode_uint_array(result_hex: str) -> List[int]:
    return [int(x) for x in abi_decode(["uint256[]"], _strip(result_hex))[0]]


# ============================================================================
# Route candidate generation (used by the quote engine). Pure: produces
# candidate Route lists; the server prices each via getAmountsOut and keeps the
# best. Works for curated AND custom tokens.
# ============================================================================
def candidate_routes(chain_id: int, token_in: str, token_out: str) -> List[List[Route]]:
    """token_in / token_out are real ERC20 addresses (native ETH already mapped
    to WETH by the caller). Returns a small set of plausible routes."""
    a = aerodrome_for(chain_id)
    factory = a["pool_factory"]
    weth = a["weth"]
    # USDC on Base (a common routing hub).
    usdc = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    ti, to = _addr(token_in), _addr(token_out)

    cands: List[List[Route]] = []

    def add(route: List[Tuple[str, str, bool]]) -> None:
        full = [(f, t, s, factory) for (f, t, s) in route]
        if full not in cands:
            cands.append(full)

    # Direct, both pool variants.
    add([(ti, to, False)])
    add([(ti, to, True)])
    # Via WETH (volatile legs) when neither endpoint is WETH.
    if ti.lower() != weth.lower() and to.lower() != weth.lower():
        add([(ti, weth, False), (weth, to, False)])
    # Via USDC (volatile legs) when neither endpoint is USDC.
    if ti.lower() != usdc.lower() and to.lower() != usdc.lower():
        add([(ti, usdc, False), (usdc, to, False)])
    return cands


# ============================================================================
# Calldata decoding for the simulation/review screen. The server's simple
# decoder can't handle dynamic types (arrays/structs); this one does, using
# eth_abi, so the review screen shows a clear human summary of DeFi actions.
# Returns None for selectors we don't own (server falls back to its own table).
# ============================================================================
def _short(addr: str) -> str:
    return addr[:6] + "…" + addr[-4:]


def decode(data: str) -> Optional[Dict[str, Any]]:
    d = (data or "").removeprefix("0x")
    if len(d) < 8:
        return None
    selector = "0x" + d[:8].lower()
    body = bytes.fromhex(d[8:]) if len(d) > 8 else b""

    S = SELECTORS
    try:
        if selector == S["swapExactTokensForTokens"]:
            amt_in, amt_min, routes, to, deadline = abi_decode(
                ["uint256", "uint256", "(address,address,bool,address)[]", "address", "uint256"], body)
            return _swap_summary("swapExactTokensForTokens", amt_in, amt_min, routes, to, deadline)
        if selector == S["swapExactETHForTokens"]:
            amt_min, routes, to, deadline = abi_decode(
                ["uint256", "(address,address,bool,address)[]", "address", "uint256"], body)
            return _swap_summary("swapExactETHForTokens", None, amt_min, routes, to, deadline)
        if selector == S["swapExactTokensForETH"]:
            amt_in, amt_min, routes, to, deadline = abi_decode(
                ["uint256", "uint256", "(address,address,bool,address)[]", "address", "uint256"], body)
            return _swap_summary("swapExactTokensForETH", amt_in, amt_min, routes, to, deadline)
        if selector == S["createLock"]:
            value, dur = abi_decode(["uint256", "uint256"], body)
            return _ok("createLock(value, lockDuration)",
                       {"value_wei": str(value), "lock_duration_days": dur // 86400})
        if selector == S["increaseAmount"]:
            tid, value = abi_decode(["uint256", "uint256"], body)
            return _ok("increaseAmount(tokenId, value)",
                       {"tokenId": str(tid), "value_wei": str(value)})
        if selector == S["increaseUnlockTime"]:
            tid, dur = abi_decode(["uint256", "uint256"], body)
            return _ok("increaseUnlockTime(tokenId, lockDuration)",
                       {"tokenId": str(tid), "lock_duration_days": dur // 86400})
        if selector == S["vote"]:
            tid, pools, weights = abi_decode(["uint256", "address[]", "uint256[]"], body)
            total = sum(int(w) for w in weights) or 1
            pretty = ", ".join(
                f"{_short(p)}={round(100 * int(w) / total)}%" for p, w in zip(pools, weights))
            return _ok("vote(tokenId, pools, weights)",
                       {"tokenId": str(tid), "allocation": pretty or "(none)"})
        if selector == S["reset"]:
            (tid,) = abi_decode(["uint256"], body)
            return _ok("reset(tokenId) – clear votes", {"tokenId": str(tid)})
        if selector == S["rd_claim"]:
            (tid,) = abi_decode(["uint256"], body)
            return _ok("claim(tokenId) – rebase", {"tokenId": str(tid)})
        if selector == S["claimRewards"]:
            (gauges,) = abi_decode(["address[]"], body)
            return _ok("claimRewards(gauges) – LP emissions",
                       {"gauges": ", ".join(_short(g) for g in gauges)})
        if selector == S["claimFees"]:
            fees, tokens, tid = abi_decode(["address[]", "address[][]", "uint256"], body)
            return _ok("claimFees(...) – voting fees",
                       {"tokenId": str(tid), "reward_contracts": str(len(fees))})
        if selector == S["claimBribes"]:
            bribes, tokens, tid = abi_decode(["address[]", "address[][]", "uint256"], body)
            return _ok("claimBribes(...) – voting bribes",
                       {"tokenId": str(tid), "reward_contracts": str(len(bribes))})
    except Exception:
        return None
    return None


def _ok(function: str, args: Dict[str, Any], warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"selector": None, "function": function, "args": args, "warnings": warnings or []}


def _swap_summary(name: str, amt_in: Optional[int], amt_min: int,
                  routes: Any, to: str, deadline: int) -> Dict[str, Any]:
    hops = " → ".join(
        [_short(routes[0][0])] + [_short(r[1]) for r in routes]) if routes else "(empty)"
    flags = ", ".join(("stable" if r[2] else "volatile") for r in routes)
    args = {
        "path": hops,
        "pools": flags,
        "min_received_wei": str(amt_min),
        "recipient": _short(to),
    }
    if amt_in is not None:
        args["amount_in_wei"] = str(amt_in)
    return _ok(f"{name}(...)", args)
