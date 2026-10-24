import math
def calculate_pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n == 0 or n != len(y):
        return 0.0
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(i * j for i, j in zip(x, y))
    sum_x_sq = sum(i**2 for i in x)
    sum_y_sq = sum(i**2 for i in y)

    numerator = (n * sum_xy) - (sum_x * sum_y)
    denominator = math.sqrt(max(0, ((n * sum_x_sq) - sum_x**2) * ((n * sum_y_sq) - sum_y**2)))

    if denominator == 0:
        return 0.0
    return numerator / denominator

print(calculate_pearson([1,2,3], [-1,-2,-3]))
