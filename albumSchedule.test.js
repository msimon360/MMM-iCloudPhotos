const test = require("node:test");
const assert = require("node:assert/strict");
const schedule = require("./albumSchedule");

const seasons = [
  { album: "Spring", month: 3, day: 20 },
  { album: "Summer", month: 6, day: 21 },
  { album: "Fall", month: 9, day: 22 },
  { album: "Winter", month: 12, day: 21 },
];

test("Fall is active on 2026-11-22", () => {
  const active = schedule.activeEntry(seasons, new Date(2026, 10, 22));
  assert.equal(active.album, "Fall");
});

test("each season starts on its month and day and runs until the next", () => {
  assert.equal(schedule.activeEntry(seasons, new Date(2026, 2, 20)).album, "Spring");
  assert.equal(schedule.activeEntry(seasons, new Date(2026, 5, 20)).album, "Spring");
  assert.equal(schedule.activeEntry(seasons, new Date(2026, 5, 21)).album, "Summer");
  assert.equal(schedule.activeEntry(seasons, new Date(2026, 8, 21)).album, "Summer");
  assert.equal(schedule.activeEntry(seasons, new Date(2026, 8, 22)).album, "Fall");
  assert.equal(schedule.activeEntry(seasons, new Date(2026, 11, 20)).album, "Fall");
  assert.equal(schedule.activeEntry(seasons, new Date(2026, 11, 21)).album, "Winter");
  assert.equal(schedule.activeEntry(seasons, new Date(2027, 2, 19)).album, "Winter");
});

test("schedule names are synced as shared albums", () => {
  assert.equal(schedule.sharedAlbumName("Fall"), "shared:Fall");
  assert.equal(schedule.sharedAlbumName("shared:Fall"), "shared:Fall");
});
