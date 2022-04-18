let config = {
    "mqtt": {
        host: "ws://kalmitTimo.local:8083",
        username: "",
        password: "",
        baseTopic: "k2"
    },
    "power": {
        "min": 80,
        "max": 180
    }
}

let workouts = [{
    name: "Low Cadence Strength Builder",
    duration: 960,
    videoId: "VUEOu5m3oaY",
    start: 4,
    levels: [
        {duration: 60, effort: 2}, // 00:04

        {duration: 60, effort: 5}, // 01:04
        {duration: 60, effort: 8}, // 02:04
        {duration: 60, effort: 2}, // 03:04

        {duration: 30, effort: 7}, // 04:04
        {duration: 30, effort: 7}, // 04:34
        {duration: 30, effort: 7}, // 05:04
        {duration: 30, effort: 7}, // 05:34
        {duration: 30, effort: 7}, // 06:04
        {duration: 30, effort: 7}, // 06:34

        {duration: 60, effort: 2}, // 07:04

        {duration: 30, effort: 7}, // 08:04
        {duration: 30, effort: 7}, // 08:34
        {duration: 30, effort: 7}, // 09:04
        {duration: 30, effort: 7}, // 09:34
        {duration: 30, effort: 7}, // 10:04
        {duration: 30, effort: 7}, // 10:34

        {duration: 60, effort: 2}, // 11:04

        {duration: 30, effort: 7}, // 12:04
        {duration: 30, effort: 7}, // 12:34
        {duration: 30, effort: 7}, // 13:04
        {duration: 30, effort: 7}, // 13:34
        {duration: 30, effort: 7}, // 14:04
        {duration: 30, effort: 7}, // 14:34

        {duration: 60, effort: 2}, // 15:03
    ]
}];

export {config, workouts};