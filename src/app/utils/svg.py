def sparkline_points(values, width=320, height=60, pad=4):
    if not values: return ""
    minv = min(values); maxv = max(values); rng = (maxv - minv) or 1.0
    n = len(values); step = (width - 2*pad) / max(1, n-1)
    pts = []
    for i, v in enumerate(values):
        x = pad + i*step
        y = height - pad - ((v - minv) / rng) * (height - 2*pad)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)

