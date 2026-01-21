/**
 * Утилиты для работы с валютами
 * Конвертация USD в RUB и форматирование цен
 */

// Курс конвертации USD к RUB (можно обновлять при необходимости)
export const USD_TO_RUB_RATE = 90;

/**
 * Конвертирует сумму из USD в RUB
 * @param usdAmount - сумма в USD
 * @returns сумма в RUB
 */
export const convertUsdToRub = (usdAmount: number): number => {
  return usdAmount * USD_TO_RUB_RATE;
};

/**
 * Форматирует сумму в рублях с символом ₽
 * @param amount - сумма
 * @param decimals - количество знаков после запятой (по умолчанию 2)
 * @returns отформатированная строка с символом рубля
 */
export const formatRubles = (amount: number, decimals: number = 2): string => {
  const formatted = amount.toLocaleString('ru-RU', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `${formatted} ₽`;
};

/**
 * Конвертирует сумму из USD в RUB и форматирует ее
 * @param usdAmount - сумма в USD
 * @param decimals - количество знаков после запятой (по умолчанию 2)
 * @returns отформатированная строка в рублях
 */
export const formatUsdAsRubles = (usdAmount: number, decimals: number = 2): string => {
  const rubAmount = convertUsdToRub(usdAmount);
  return formatRubles(rubAmount, decimals);
};

/**
 * Форматирует сумму в долларах с символом $
 * @param amount - сумма
 * @param decimals - количество знаков после запятой (по умолчанию 2)
 * @returns отформатированная строка с символом доллара
 */
export const formatDollars = (amount: number, decimals: number = 2): string => {
  const formatted = amount.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `$${formatted}`;
};

/**
 * Определяет, является ли строка ценой в долларах
 * @param priceString - строка с ценой
 * @returns true если строка содержит цену в долларах
 */
export const isDollarPrice = (priceString: string): boolean => {
  return /^\$[0-9]+\.?[0-9]*$/.test(priceString);
};

/**
 * Конвертирует строку с ценой из долларов в рубли
 * @param priceString - строка с ценой в долларах (например, "$10.50")
 * @returns строка с ценой в рублях (например, "945.00 ₽")
 */
export const convertDollarStringToRubles = (priceString: string): string => {
  if (!isDollarPrice(priceString)) {
    return priceString; // Возвращаем как есть, если это не цена в долларах
  }
  
  const numericValue = parseFloat(priceString.replace('$', ''));
  if (isNaN(numericValue)) {
    return priceString;
  }
  
  return formatUsdAsRubles(numericValue);
};