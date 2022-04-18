import {config} from './config.mjs';

// Create a client instance
const k2 = mqtt.connect(config.mqtt.host, {
    username: config.mqtt.username,
    password: config.mqtt.password,
    clean: true,
    reconnectPeriod: 1000,
    connectTimeout: 5 * 1000
});

// connect the client
k2.on("connect", () => {
    console.log("[MQTT] Connected");

    /* subscribe to k2 updates */
    k2.subscribe(`${config.mqtt.baseTopic}/status/+`);
    k2.subscribe(`${config.mqtt.baseTopic}/kettler/+`);
    k2.subscribe(`${config.mqtt.baseTopic}/log/+`);
});

k2.on("message", (topic, message) => {
    console.log(topic, message.toString());
});

k2.startLog = function() {
    console.log("StartLog");
}

k2.closeLog = function() {
    console.log("CloseLog");
}

k2.setEffortLevel = function(effort) {
    switch(effort) {
        case "start":
            k2.startLog();
            break;
        case "end":
            k2.closeLog();
            break;
        default:
            let power = config.power.min + ((config.power.max - config.power.min) / 10) * effort;
            k2.publish(`${config.mqtt.baseTopic}/kettler/cmnd/power`, `${power}`);
            break;
    }
}

export {k2};