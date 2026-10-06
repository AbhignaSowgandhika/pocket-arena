"""
world.py - the map: walls, bushes, goals, bases and where wild creatures live.

The map is mirrored: everything on the Blue (left) side has a twin on the Red
(right) side, so neither team has an advantage. `mirror(x)` flips a position
across the middle of the map.
"""
import heapq

from pygame.math import Vector2 as V

from .settings import (BLUE, RED, WORLD_W, WORLD_H, GOAL_RADIUS,
                       OUTER_GOAL_POINTS, INNER_GOAL_POINTS)


def mirror(x):
    return WORLD_W - x


class Rect:
    """An axis-aligned rectangle. Used for walls and bushes."""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    def contains(self, p):
        return self.x <= p.x <= self.right and self.y <= p.y <= self.bottom

    def grown(self, by):
        return Rect(self.x - by, self.y - by, self.w + 2 * by, self.h + 2 * by)

    def segment_hits(self, a, b):
        """True if the straight line from a to b passes through this rectangle.
        (The 'slab' method: clip the line against the x and y ranges.)"""
        t0, t1 = 0.0, 1.0
        d = b - a
        for start, delta, lo, hi in ((a.x, d.x, self.x, self.right),
                                     (a.y, d.y, self.y, self.bottom)):
            if abs(delta) < 1e-9:
                if start < lo or start > hi:
                    return False
            else:
                ta, tb = (lo - start) / delta, (hi - start) / delta
                if ta > tb:
                    ta, tb = tb, ta
                t0, t1 = max(t0, ta), min(t1, tb)
                if t0 > t1:
                    return False
        return True


class Goal:
    """A scoring zone. `team` is the team that DEFENDS it."""

    def __init__(self, team, pos, capacity, inner=False):
        self.team = team
        self.pos = V(pos)
        self.capacity = capacity
        self.points = 0
        self.inner = inner
        self.broken = False

    @property
    def remaining(self):
        return max(0, self.capacity - self.points)

    def contains(self, p):
        return self.pos.distance_to(p) <= GOAL_RADIUS


class World:
    def __init__(self):
        W, H = WORLD_W, WORLD_H
        mid = H / 2

        # Walls on the Blue half; the Red half is a mirror image.
        left_walls = [
            Rect(560, 430, 640, 64),            # separates top lane from jungle
            Rect(560, H - 430 - 64, 640, 64),   # separates bottom lane from jungle
            Rect(330, 560, 54, 150),            # base cover, upper
            Rect(330, H - 560 - 150, 54, 150),  # base cover, lower
        ]
        self.walls = left_walls + [Rect(mirror(r.right), r.y, r.w, r.h) for r in left_walls]
        self.walls.append(Rect(W / 2 - 60, mid - 150, 120, 300))   # centre rock

        left_bushes = [
            Rect(980, 150, 260, 150),            # top lane
            Rect(980, H - 150 - 150, 260, 150),  # bottom lane
            Rect(820, mid - 110, 170, 220),      # jungle
        ]
        self.bushes = left_bushes + [Rect(mirror(r.right), r.y, r.w, r.h) for r in left_bushes]

        self.bases = {BLUE: V(150, mid), RED: V(mirror(150), mid)}

        self.goals = []
        for team, fx in ((BLUE, lambda x: x), (RED, mirror)):
            self.goals.append(Goal(team, (fx(560), 250), OUTER_GOAL_POINTS))
            self.goals.append(Goal(team, (fx(560), H - 250), OUTER_GOAL_POINTS))
            self.goals.append(Goal(team, (fx(400), mid), INNER_GOAL_POINTS, inner=True))

        # (kind, position) for every wild creature camp
        self.wild_spots = []
        for fx in (lambda x: x, mirror):
            self.wild_spots += [
                ("sunshine", V(fx(900), 250)),
                ("sunshine", V(fx(900), H - 250)),
                ("sunshine", V(fx(1180), mid - 230)),
                ("sunshine", V(fx(1180), mid + 230)),
                ("moonshine", V(fx(650), mid)),
            ]
        self.wild_spots.append(("sunshine", V(W / 2, 250)))
        self.wild_spots.append(("sunshine", V(W / 2, H - 250)))

        # Each bot heads for one of these "lanes" when it has nothing better to do.
        self.lane_anchor = {
            "top": lambda team: V(W / 2 + (-300 if team == BLUE else 300), 250),
            "bottom": lambda team: V(W / 2 + (-300 if team == BLUE else 300), H - 250),
            "jungle": lambda team: V(W / 2 + (-420 if team == BLUE else 420), mid - 240),
        }

        self._build_nav()

    # --- goals ------------------------------------------------------------------
    def goal_is_open(self, goal):
        """Inner goals only open after one of that team's outer goals breaks."""
        if goal.broken:
            return False
        if not goal.inner:
            return True
        return any(g.broken for g in self.goals if g.team == goal.team and not g.inner)

    # --- movement ---------------------------------------------------------------
    def bush_at(self, p):
        for i, b in enumerate(self.bushes):
            if b.contains(p):
                return i
        return None

    def collide(self, pos, radius):
        """Push a circle (a character) out of any wall and keep it on the map."""
        for r in self.walls:
            cx = min(max(pos.x, r.x), r.right)
            cy = min(max(pos.y, r.y), r.bottom)
            dx, dy = pos.x - cx, pos.y - cy
            dist_sq = dx * dx + dy * dy
            if dist_sq >= radius * radius:
                continue
            if dist_sq > 1e-9:
                dist = dist_sq ** 0.5
                pos.x += dx / dist * (radius - dist)
                pos.y += dy / dist * (radius - dist)
            else:  # centre is inside the wall: leave by the closest side
                exits = [(pos.x - r.x, -1, 0), (r.right - pos.x, 1, 0),
                         (pos.y - r.y, 0, -1), (r.bottom - pos.y, 0, 1)]
                d, ex, ey = min(exits)
                pos.x += ex * (d + radius)
                pos.y += ey * (d + radius)
        pos.x = min(max(pos.x, radius), WORLD_W - radius)
        pos.y = min(max(pos.y, radius), WORLD_H - radius)

    def clear_line(self, a, b, margin=18):
        return not any(w.grown(margin).segment_hits(a, b) for w in self.walls)

    # --- path finding (used by the bots) -------------------------------------------
    def _build_nav(self):
        """Put a waypoint just outside each wall corner, then connect every pair
        of waypoints that can see each other. Bots walk this graph around walls."""
        self.nodes = []
        for w in self.walls:
            g = w.grown(34)
            for p in (V(g.x, g.y), V(g.right, g.y), V(g.x, g.bottom), V(g.right, g.bottom)):
                if 0 < p.x < WORLD_W and 0 < p.y < WORLD_H and not any(
                        o.grown(20).contains(p) for o in self.walls):
                    self.nodes.append(p)
        self.links = {i: [] for i in range(len(self.nodes))}
        for i, a in enumerate(self.nodes):
            for j in range(i + 1, len(self.nodes)):
                b = self.nodes[j]
                if self.clear_line(a, b):
                    d = a.distance_to(b)
                    self.links[i].append((j, d))
                    self.links[j].append((i, d))

    def next_step(self, start, goal):
        """Where to walk next to reach `goal` from `start` without hitting walls."""
        if self.clear_line(start, goal):
            return V(goal)
        starts = [(i, start.distance_to(n)) for i, n in enumerate(self.nodes)
                  if self.clear_line(start, n)]
        ends = {i: goal.distance_to(n) for i, n in enumerate(self.nodes)
                if self.clear_line(goal, n)}
        if not starts or not ends:
            return V(goal)
        # Dijkstra's algorithm: always expand the cheapest path found so far.
        best = {}
        first = {}
        heap = []
        for i, d in starts:
            heapq.heappush(heap, (d, i, i))
        while heap:
            d, i, origin = heapq.heappop(heap)
            if i in best:
                continue
            best[i], first[i] = d, origin
            for j, step in self.links[i]:
                if j not in best:
                    heapq.heappush(heap, (d + step, j, origin))
        reachable = [(best[i] + ends[i], i) for i in ends if i in best]
        if not reachable:
            return V(goal)
        _, end_node = min(reachable)
        return V(self.nodes[first[end_node]])
