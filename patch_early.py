#!/usr/bin/env python3
"""Impulse may enter on a 1/3 lean. A late burst blocks the slow lane for 45 minutes."""
import os
import shutil
import py_compile

TARGET = "main.py"
BACKUP = "main.py.bak_early"

REPLACEMENTS = [
(
"""    async def evaluate_and_enter(strategy, symbol, regime: str):
        claimed = False
        async with symbol_locks[symbol]:
""",
"""    async def evaluate_and_enter(strategy, symbol, regime: str):
        claimed = False
        if slow_lane_blocked(symbol):
            return False
        async with symbol_locks[symbol]:
"""
),
(
"""        ok_idx, why_idx = index_entry_allowed(idx_now, side)
        if not ok_idx:
            logger.info(f"🚫 IMPULSE index {symbol} | {why_idx}")
            return
""",
"""        ok_idx, why_idx = index_entry_allowed(idx_now, side)
        if not ok_idx:
            direction = str((idx_now or {}).get("direction") or "NEUTRAL").upper()
            agree = int((idx_now or {}).get("agree") or 0)
            lean_ok = agree == 1 and (
                (side == "BUY" and direction == "BULL")
                or (side == "SELL" and direction == "BEAR")
            )
            if not lean_ok:
                logger.info(f"🚫 IMPULSE index {symbol} | {why_idx}")
                return
            logger.info(f"⚡ IMPULSE lean {symbol} | {direction} {agree}/3 {side}")
"""
),
(
"""def impulse_scan_row(row: dict, now: float) -> None:
""",
"""_slow_lane_until = {}

def mark_slow_lane_block(symbol: str, now: float) -> None:
    _slow_lane_until[symbol] = float(now) + 45.0 * 60.0
    logger.info(f"🚫 slow lane {symbol} | 45m after a late impulse")

def slow_lane_blocked(symbol: str) -> bool:
    until = _slow_lane_until.get(symbol)
    if not until:
        return False
    if datetime.now(timezone.utc).timestamp() >= until:
        _slow_lane_until.pop(symbol, None)
        return False
    return True

def impulse_scan_row(row: dict, now: float) -> None:
"""
),
(
"""    if abs(chg) < lo or abs(chg) > hi:
        return
""",
"""    if abs(chg) < lo:
        return
    if abs(chg) > hi:
        _impulse_next[sym] = now + 20.0
        mark_slow_lane_block(sym, now)
        logger.info(f"🚫 IMPULSE late {sym} | burst={chg:+.2f}% over {hi:.1f}%")
        return
"""
),
(
"""        _impulse_next[sym] = now + 20.0
        logger.info(f"🚫 IMPULSE late {sym} | burst={chg:+.2f}% already {prior:+.2f}%")
        return
""",
"""        _impulse_next[sym] = now + 20.0
        mark_slow_lane_block(sym, now)
        logger.info(f"🚫 IMPULSE late {sym} | burst={chg:+.2f}% already {prior:+.2f}%")
        return
"""
),
]


def main():
    if not os.path.exists(TARGET):
        print(f"STOPPED missing {TARGET}")
        return
    shutil.copy2(TARGET, BACKUP)
    text = open(TARGET, encoding="utf-8").read()
    for i, (old, new) in enumerate(REPLACEMENTS, 1):
        n = text.count(old)
        if n != 1:
            shutil.copy2(BACKUP, TARGET)
            print(f"STOPPED piece {i} count={n}")
            print(f"restored from {BACKUP} — bot file was not changed")
            return
        text = text.replace(old, new, 1)
    open(TARGET, "w", encoding="utf-8").write(text)
    try:
        py_compile.compile(TARGET, doraise=True)
    except Exception as e:
        shutil.copy2(BACKUP, TARGET)
        print(f"STOPPED compile: {e}")
        print(f"restored from {BACKUP} — bot file was not changed")
        return
    print(f"DONE pieces={len(REPLACEMENTS)}")
    print(f"backup={BACKUP}")


if __name__ == "__main__":
    main()
