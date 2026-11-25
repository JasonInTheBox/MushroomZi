const millisecondsPerDay = 86_400_000;

/**
 * @param {number} timestamp Unix-epoch milliseconds.
 * @param {number} passageCount Eligible passages in corpus order.
 */
export function getDailyPassageIndex(timestamp, passageCount) {
    if (passageCount <= 0) return -1;

    const utcDay = Math.floor(timestamp / millisecondsPerDay);
    return ((utcDay % passageCount) + passageCount) % passageCount;
}
