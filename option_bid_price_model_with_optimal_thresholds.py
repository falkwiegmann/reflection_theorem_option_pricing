import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.stats import norm


def pr_below_threshold_at_expiry(S_0, threshold, days, daily_std):
    """Probability of stock price being below threshold at expiry."""
    x = (threshold - S_0) / (np.sqrt(days) * daily_std)
    return norm.cdf(x)


def pr_below_threshold_anytime(S_0, threshold, days, daily_std):
    """Probability of stock reaching below threshold at any point during [0, T].
    Uses the reflection principle: P(ever reach T) = 2 * P(below T at expiry)."""
    return np.minimum(2 * pr_below_threshold_at_expiry(S_0, threshold, days, daily_std), 1)


def run(S_0, strike, days, volatility, save_path=None):
    daily_std = volatility * S_0

    thresholds = np.linspace(3/4 * strike, strike, 500)
    o_bps = np.linspace(0, 2 * (strike - S_0), 500)

    p_at_expiry = pr_below_threshold_at_expiry(S_0, thresholds, days, daily_std)
    p_anytime = pr_below_threshold_anytime(S_0, thresholds, days, daily_std)

    fig, axs = plt.subplots(1, 2, figsize=(15, 5))

    # Left: probability curves
    axs[0].plot(thresholds, p_at_expiry, label='at time t=T')
    axs[0].plot(thresholds, p_anytime, label='at some point 0 <= t <= T')
    axs[0].set_title(f'Probability of P_t < threshold given P_0 = {S_0}')
    axs[0].set_xlabel('Threshold')
    axs[0].set_ylabel('Probability')
    axs[0].grid()
    axs[0].legend()

    # Right: expected P&L heatmap
    pl_grid = np.zeros((len(thresholds), len(o_bps)))
    for i, threshold in enumerate(thresholds):
        for j, o_bp in enumerate(o_bps):
            pl_no_reach = max(strike - S_0 - o_bp, -o_bp)
            pl_reach = strike - threshold - o_bp
            pl_grid[i, j] = (1 - p_anytime[i]) * pl_no_reach + p_anytime[i] * pl_reach

    color_norm = mcolors.TwoSlopeNorm(
        vmin=pl_grid.min(), vcenter=0, vmax=pl_grid.max())
    mesh = axs[1].pcolormesh(
        thresholds, o_bps, pl_grid.T, shading='auto', cmap='RdYlGn', norm=color_norm)

    contour = axs[1].contour(thresholds, o_bps, pl_grid.T, levels=[0], colors='black', linewidths=2)
    axs[1].clabel(contour, fmt='%1.1f', colors='red')

    # Blue line: optimal threshold (max P&L) for each o_bp
    best_threshold_idx = np.argmax(pl_grid, axis=0)
    best_thresholds = thresholds[best_threshold_idx]
    best_pl = pl_grid.T[np.arange(len(o_bps)), best_threshold_idx]

    # Find limiting o_bp where max P&L crosses zero
    i_target = np.argmin(np.abs(best_pl))
    o_bp_target = o_bps[i_target]

    axs[1].plot(best_thresholds, o_bps, color='blue', linewidth=2,
                label=f'Max P/L at T=${np.max(best_thresholds):.2f}\nP/L=0 when o_bp=${o_bp_target:.2f}')
    axs[1].set_title(f'Optimal o_bp for threshold and P/L given P_0 = {S_0}, strike = {strike}')
    axs[1].set_xlabel('Threshold (to buy stock at)')
    axs[1].set_ylabel('o_bp')
    axs[1].grid()
    axs[1].legend()
    fig.colorbar(mesh, ax=axs[1])

    fig.tight_layout()

    print(f"Limiting bid price: o_bp = ${o_bp_target:.2f}")
    print(f"Optimal threshold:  T = ${best_thresholds[i_target]:.2f}")

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved to {save_path}")
    else:
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Find optimal stock buying threshold for each option bid price. '
                    'Generates a P&L heatmap.')
    parser.add_argument('--stock-price', type=float, default=17,
                        help='Current stock price S_0 (default: 17)')
    parser.add_argument('--strike', type=float, default=18.5,
                        help='Put option strike price (default: 18.5)')
    parser.add_argument('--days', type=float, default=2,
                        help='Days to expiration (default: 2)')
    parser.add_argument('--volatility', type=float, default=0.02,
                        help='Daily volatility as fraction of stock price (default: 0.02)')
    parser.add_argument('--save', type=str, default=None, metavar='PATH',
                        help='Save figure to file instead of displaying')
    args = parser.parse_args()

    run(args.stock_price, args.strike, args.days, args.volatility, args.save)
