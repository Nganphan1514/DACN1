import numpy as np

LEFT_EYE = [
    33, 160, 158,
    133, 153, 144
]

RIGHT_EYE = [
    362, 385, 387,
    263, 373, 380
]

MOUTH = [
    61, 13,
    291, 14
]


def distance(p1, p2):
    return np.linalg.norm(
        np.array(p1) - np.array(p2)
    )


def calculate_ear(points):

    A = distance(points[1], points[5])

    B = distance(points[2], points[4])

    C = distance(points[0], points[3])

    return (A + B) / (2 * C)


def calculate_mar(points):

    vertical = distance(
        points[1],
        points[3]
    )

    horizontal = distance(
        points[0],
        points[2]
    )

    return (
        vertical /
        horizontal
    )