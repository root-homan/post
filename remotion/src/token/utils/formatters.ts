const currencyFormatter = Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const compactCurrencyFormatter = Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

const percentageFormatter = Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 0,
});

export const formatCurrency = (value: number): string => {
  return currencyFormatter.format(value);
};

export const formatCurrencyCompact = (value: number): string => {
  return compactCurrencyFormatter.format(value);
};

export const formatPercentage = (value: number): string => {
  return percentageFormatter.format(value / 100);
};
