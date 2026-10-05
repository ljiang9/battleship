"""海战棋 Battleship: 10x10 海战棋打 AI。纯标准库。"""
import argparse
import random
import secrets
import sys

SIZE = 10
FLEET = [("航母", 5), ("战列舰", 4), ("巡洋舰", 3), ("驱逐舰", 3), ("潜艇", 2)]

EMPTY, SHIP, HIT, MISS = ".", "S", "X", "o"


class Board:
    """棋盘: grid 存船只位置, shots 记录射击结果。"""

    def __init__(self):
        self.grid = [[EMPTY] * SIZE for _ in range(SIZE)]
        self.shots = [[EMPTY] * SIZE for _ in range(SIZE)]
        self.ships = []  # 每艘船: (名字, [(r,c),...], 命中集合)

    def place_random(self, rng):
        for name, length in FLEET:
            for _ in range(1000):
                horiz = rng.randrange(2) == 0
                if horiz:
                    r = rng.randrange(SIZE)
                    c = rng.randrange(SIZE - length + 1)
                    cells = [(r, c + i) for i in range(length)]
                else:
                    r = rng.randrange(SIZE - length + 1)
                    c = rng.randrange(SIZE)
                    cells = [(r + i, c) for i in range(length)]
                if all(self.grid[rr][cc] == EMPTY for rr, cc in cells):
                    break
            else:
                raise RuntimeError("布船失败")
            for rr, cc in cells:
                self.grid[rr][cc] = SHIP
            self.ships.append((name, cells, set()))

    def fire(self, r, c):
        """射击 (r,c): 返回 ('hit'|'miss'|'sunk'|'repeat', 船名或None)。"""
        if self.shots[r][c] != EMPTY:
            return "repeat", None
        if self.grid[r][c] == SHIP:
            self.shots[r][c] = HIT
            for name, cells, hits in self.ships:
                if (r, c) in cells:
                    hits.add((r, c))
                    if hits == set(cells):
                        return "sunk", name
                    return "hit", name
        else:
            self.shots[r][c] = MISS
            return "miss", None

    def all_sunk(self):
        return all(hits == set(cells) for _, cells, hits in self.ships)

    def ship_cells(self):
        return sum(len(c) for _, c, _ in self.ships)


class HuntTargetAI:
    """打猎-追踪 AI: 随机打猎, 命中后打相邻格追踪。"""

    def __init__(self, rng):
        self.rng = rng
        self.targets = []  # 追踪队列
        self.tried = set()

    def choose(self):
        while self.targets:
            mv = self.targets.pop(0)
            if mv not in self.tried:
                self.tried.add(mv)
                return mv
        while True:
            mv = (self.rng.randrange(SIZE), self.rng.randrange(SIZE))
            if mv not in self.tried:
                self.tried.add(mv)
                return mv

    def feedback(self, r, c, result):
        if result in ("hit", "sunk"):
            if result == "sunk":
                self.targets = []  # 击沉后清空追踪
            else:
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < SIZE and 0 <= nc < SIZE and (nr, nc) not in self.tried:
                        self.targets.append((nr, nc))


def parse_coord(text):
    """'B5' -> (4,1)。无效抛 ValueError。"""
    t = text.strip().upper()
    if len(t) < 2 or len(t) > 3:
        raise ValueError("坐标格式不对")
    col = ord(t[0]) - ord("A")
    try:
        row = int(t[1:]) - 1
    except ValueError:
        raise ValueError("坐标格式不对")
    if not (0 <= col < SIZE and 0 <= row < SIZE):
        raise ValueError("坐标超出棋盘")
    return row, col


def to_coord(r, c):
    return f"{chr(ord('A') + c)}{r + 1}"


def render(shots, ships=None, reveal=False):
    head = "   " + " ".join(chr(ord("A") + c) for c in range(SIZE))
    lines = [head]
    for r in range(SIZE):
        row = []
        for c in range(SIZE):
            ch = shots[r][c]
            if reveal and ships is not None and ch == EMPTY and ships[r][c] == SHIP:
                ch = "S"
            row.append(ch)
        lines.append(f"{r + 1:2d} " + " ".join(row))
    return "\n".join(lines)


def play_interactive(seed=None):
    rng = random.Random(seed) if seed is not None else secrets.SystemRandom()
    me = Board()
    me.place_random(rng)
    ai_board = Board()
    ai_board.place_random(rng)
    ai = HuntTargetAI(rng)
    my_shots = 0
    print("海战棋! 你的舰队已自动布好。输入坐标射击(如 B5), q 退出。")
    while True:
        print("\n敌方海域:")
        print(render(ai_board.shots))
        if ai_board.all_sunk():
            print(f"\n🎉 胜利! 你用了 {my_shots} 次射击击沉全部敌舰。")
            return
        if me.all_sunk():
            print("\n💥 你的舰队全灭, AI 获胜。")
            print("你的海域(揭晓):")
            print(render(me.shots, me.grid, reveal=True))
            return
        try:
            text = input("射击> ").strip()
        except EOFError:
            print("\n再见。")
            return
        if text.lower() == "q":
            print("已退出。")
            return
        try:
            r, c = parse_coord(text)
        except ValueError as e:
            print(f"坐标无效: {e}, 请重输 (如 B5)。")
            continue
        result, name = ai_board.fire(r, c)
        if result == "repeat":
            print("这里已经射击过了, 换一格。")
            continue
        my_shots += 1
        if result == "sunk":
            print(f"💥 击沉敌方 {name}!")
        elif result == "hit":
            print("🎯 命中!")
        else:
            print("🌊 未命中。")
        # AI 回合
        ar, ac = ai.choose()
        ares, aname = me.fire(ar, ac)
        ai.feedback(ar, ac, ares)
        if ares == "sunk":
            print(f"⚠️ AI 击沉了你的 {aname}! ({to_coord(ar, ac)})")
        elif ares == "hit":
            print(f"⚠️ AI 命中了你的舰船! ({to_coord(ar, ac)})")


def play_demo(seed=7):
    rng = random.Random(seed)
    ai_board = Board()
    ai_board.place_random(rng)
    ai = HuntTargetAI(rng)
    shots = 0
    while not ai_board.all_sunk() and shots < 200:
        r, c = ai.choose()
        result, _ = ai_board.fire(r, c)
        ai.feedback(r, c, result)
        shots += 1
    print(f"演示结束: {shots} 次射击, 敌舰{'全灭' if ai_board.all_sunk() else '未全灭'}。")


def play_selfplay(seed=3):
    rng = random.Random(seed)
    b1, b2 = Board(), Board()
    b1.place_random(rng)
    b2.place_random(rng)
    ai1, ai2 = HuntTargetAI(rng), HuntTargetAI(rng)
    turn = 0
    while turn < 400:
        if turn % 2 == 0:
            r, c = ai1.choose()
            res, _ = b2.fire(r, c)
            ai1.feedback(r, c, res)
            if b2.all_sunk():
                print(f"自我对战: 先手胜, 用时 {turn // 2 + 1} 回合。")
                return "first"
        else:
            r, c = ai2.choose()
            res, _ = b1.fire(r, c)
            ai2.feedback(r, c, res)
            if b1.all_sunk():
                print(f"自我对战: 后手胜, 用时 {turn // 2 + 1} 回合。")
                return "second"
        turn += 1
    print("自我对战: 400 回合未分胜负。")
    return "draw"


def main(argv=None):
    p = argparse.ArgumentParser(description="海战棋: 10x10 打猎-追踪 AI。")
    p.add_argument("--demo", action="store_true", help="AI 演示攻击")
    p.add_argument("--selfplay", action="store_true", help="AI 自我对战")
    p.add_argument("--seed", type=int, default=None, help="随机种子")
    args = p.parse_args(argv)
    if args.demo:
        play_demo(args.seed if args.seed is not None else 7)
    elif args.selfplay:
        play_selfplay(args.seed if args.seed is not None else 3)
    else:
        if not sys.stdin.isatty():
            print("error: 交互模式需要终端, 管道请用 --demo/--selfplay。", file=sys.stderr)
            sys.exit(2)
        play_interactive(args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
