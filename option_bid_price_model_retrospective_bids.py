import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# np.trapz was renamed to np.trapezoid in NumPy 2.0
_trapz = getattr(np, 'trapezoid', None) or np.trapz


def pr_below_threshold_at_expiry(S_0, threshold, days, daily_std):
    """Probability of stock price being below threshold at expiry."""
    x = (threshold - S_0) / (np.sqrt(days) * daily_std)
    return norm.cdf(x)


def pr_below_threshold_anytime(S_0, threshold, days, daily_std):
    """Probability of stock reaching below threshold at any point during [0, T].
    Uses the reflection principle: P(ever reach T) = 2 * P(below T at expiry)."""
    return np.minimum(2 * pr_below_threshold_at_expiry(S_0, threshold, days, daily_std), 1)


def put_payoff(strike, stock_price, option_price):
    """P&L from exercising a put option bought at option_price."""
    return np.maximum(strike - stock_price, 0) - option_price


def pdf_from_cdf(cdf, x):
    """Numerically differentiate a CDF to get a PDF."""
    spacing = np.mean(np.diff(x))
    gradient = np.gradient(cdf, spacing)
    gradient = np.abs(gradient) / np.abs(_trapz(gradient, x))
    return gradient


def run(S_0, strike, days, volatility, save_path=None):
    daily_std = volatility * S_0

    thresholds = np.linspace(0, 2 * S_0, 500)
    p_at_expiry = pr_below_threshold_at_expiry(S_0, thresholds, days, daily_std)
    p_anytime = pr_below_threshold_anytime(S_0, thresholds, days, daily_std)
    pdf = pdf_from_cdf(p_anytime, thresholds)

    fig, axs = plt.subplots(2, 2, figsize=(15, 7))

    # Top-left: CDF (probability of reaching threshold)
    axs[0, 0].plot(thresholds, p_at_expiry, label='at time t=T')
    axs[0, 0].plot(thresholds, p_anytime, label='at some point 0 <= t <= T')
    axs[0, 0].set_title(f'Probability of P_t < threshold given P_0 = {S_0}')
    axs[0, 0].set_xlabel('Threshold')
    axs[0, 0].set_ylabel('Probability')
    axs[0, 0].grid()
    axs[0, 0].legend()

    # Top-right: PDF of P&L for different o_bp values
    # Bottom-left: CDF mapped to P&L for different o_bp values
    o_bp_range = np.linspace(0, 2 * (strike - S_0), 7)
    for o_bp in o_bp_range:
        pl = put_payoff(strike, thresholds, o_bp)
        axs[1, 0].plot(pl, p_anytime, label=f'o_bp = {o_bp:.1f}')

        loss = np.abs(_trapz(pdf[pl < 0], pl[pl < 0]))
        profit = np.abs(_trapz(pdf[pl > 0], pl[pl > 0]))
        integral = profit - loss
        axs[0, 1].plot(pl, pdf, label=f'o_bp = {o_bp:.1f}, Integral = {integral:.2f}')

    axs[1, 0].set_title(f'Payoff of the put option given P_0 = {S_0}, strike = {strike}')
    axs[1, 0].set_xlabel('P/L')
    axs[1, 0].set_ylabel('CDF')
    axs[1, 0].grid()
    axs[1, 0].legend()

    axs[0, 1].set_title(f'PDF of the put option given P_0 = {S_0}, strike = {strike}')
    axs[0, 1].set_xlabel('P/L')
    axs[0, 1].set_ylabel('PDF')
    axs[0, 1].grid()
    axs[0, 1].legend()

    # Find risk-neutral o_bp (where expected P&L = 0)
    pl_by_obp = {}
    for o_bp in np.linspace(0, 2 * (strike - S_0), 700):
        pl = put_payoff(strike, thresholds, o_bp)
        loss = np.abs(_trapz(pdf[pl < 0], pl[pl < 0]))
        profit = np.abs(_trapz(pdf[pl > 0], pl[pl > 0]))
        pl_by_obp[o_bp] = profit - loss

    risk_neutral_obp = min(pl_by_obp, key=lambda k: abs(pl_by_obp[k]))
    threshold_for_profit = strike - risk_neutral_obp
    prob_profitable = pr_below_threshold_anytime(S_0, threshold_for_profit, days, daily_std)

    # Bottom-right: summary text
    axs[1, 1].axis('off')
    text = (f"o_bp for min P/L = {risk_neutral_obp:.2f}\n"
            f"Threshold for profitability = {threshold_for_profit:.2f}\n"
            f"Probability of being profitable = {prob_profitable * 100:.2f}%")
    axs[1, 1].text(0.5, 0.5, text, fontsize=10, ha='center', va='center', wrap=True)

    fig.suptitle(f"o_bp for min P/L = {risk_neutral_obp:.2f}, "
                 f"Threshold for profitability = {threshold_for_profit:.2f}, "
                 f"Probability of being profitable = {prob_profitable * 100:.2f}%")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved to {save_path}")
    else:
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compute P&L distribution across different option bid prices '
                    'using the reflection principle of a Wiener process.')
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
