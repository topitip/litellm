/**
 * Утилиты для работы с валютами
 * Форматирование цен в рублях
 */


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
 * Форматирует сумму в рублях
 * @param amount - сумма
 * @param decimals - количество знаков после запятой (по умолчанию 2)
 * @returns отформатированная строка в рублях
 */
export const formatRublesDirect = (amount: number, decimals: number = 2): string => {
  return formatRubles(amount, decimals);
};
