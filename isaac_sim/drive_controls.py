"""Hardware-free keyboard speed selection, shared by the GUI and tests."""


class BaseSpeed:
    SCALES = {1: 1.0, 2: 1.5, 3: 2.0}
    NAMES = {1: "NORMAL", 2: "FAST", 3: "HIGH"}

    def __init__(self, linear=0.25, angular=0.8):
        self.linear, self.angular = linear, angular
        self.level = 1

    def select(self, level):
        if level not in self.SCALES:
            raise ValueError("Base speed level must be 1, 2 or 3")
        self.level = level

    def velocity(self, forward, left, ccw):
        # Keep diagonal translation at the same speed as straight translation.
        norm = max(1.0, (forward * forward + left * left) ** 0.5)
        scale = self.SCALES[self.level]
        return (self.linear * scale * forward / norm,
                self.linear * scale * left / norm, self.angular * scale * ccw)

    @property
    def label(self):
        scale = self.SCALES[self.level]
        return (f"Base {self.level}: {self.NAMES[self.level]} | "
                f"{self.linear * scale:g} m/s, {self.angular * scale:g} rad/s | 1/2/3")
