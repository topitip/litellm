export function valueFormatter(number: number) {
  if (number >= 1000000) {
    return (number / 1000000).toFixed(2) + "M";
  }
  if (number >= 1000) {
    return number / 1000 + "k";
  }
  return number.toString();
}

import { formatUsdAsRubles } from "../../../utils/currencyUtils";

export function valueFormatterSpend(number: number) {
  if (number === 0) return "0 ₽";
  if (number >= 1000000) {
    const rubValue = formatUsdAsRubles(number / 1000000, 0);
    return rubValue.replace(" ₽", "M ₽");
  }
  if (number >= 1000) {
    const rubValue = formatUsdAsRubles(number / 1000, 0);
    return rubValue.replace(" ₽", "k ₽");
  }
  return formatUsdAsRubles(number, 0);
}
