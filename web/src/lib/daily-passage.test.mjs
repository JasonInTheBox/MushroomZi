import assert from "node:assert/strict";
import test from "node:test";
import { getDailyPassageIndex } from "./daily-passage.mjs";

test("selects the same passage throughout a UTC day", () => {
    const midnight = Date.parse("2026-11-24T00:00:00.000Z");
    const lateEvening = Date.parse("2026-11-24T23:59:59.999Z");

    assert.equal(getDailyPassageIndex(midnight, 31), getDailyPassageIndex(lateEvening, 31));
});

test("changes passage at UTC midnight", () => {
    const beforeMidnight = Date.parse("2026-11-24T23:59:59.999Z");
    const midnight = Date.parse("2026-11-25T00:00:00.000Z");

    assert.notEqual(getDailyPassageIndex(beforeMidnight, 31), getDailyPassageIndex(midnight, 31));
});

test("cycles through the pool and wraps around", () => {
    assert.equal(getDailyPassageIndex(Date.parse("1970-01-01T00:00:00Z"), 3), 0);
    assert.equal(getDailyPassageIndex(Date.parse("1970-01-02T00:00:00Z"), 3), 1);
    assert.equal(getDailyPassageIndex(Date.parse("1970-01-03T00:00:00Z"), 3), 2);
    assert.equal(getDailyPassageIndex(Date.parse("1970-01-04T00:00:00Z"), 3), 0);
});

test("maps dates before the Unix epoch to a valid index", () => {
    assert.equal(getDailyPassageIndex(Date.parse("1969-12-31T00:00:00Z"), 5), 4);
});

test("returns no selection for an empty pool", () => {
    assert.equal(getDailyPassageIndex(Date.now(), 0), -1);
});
