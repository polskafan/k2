class KettlerStatusBar {
    constructor(selector, k2) {
        this.element = document.querySelector(selector);
        this.k2 = k2;
        this.k2.on("message", this.onStatus.bind(this))
    }

    onStatus(topic, message) {
        if(topic.endsWith("kettler/data")) {
            let data = JSON.parse(message.toString()).payload;

            this.element.innerHTML = `<table class="statusBar">

<thead><tr>
<td>Time</td>
<td>Distance</td>
<td>Speed</td>
<td>Cadence</td>
<td>Power</td>
<td>Energy</td>
</tr></thead>

<tbody><tr>
<td>${data.timeElapsed}</td>
<td>${(data.distance / 1000).toFixed(1)} m</td>
<td>${data.speed.toFixed(1)} km/h</td>
<td>${data.cadence}</td>
<td>${data.realPower} / ${data.destPower} W</td>
<td>${data.energy} kJ</td>
</tr></tbody>

</table>`;
        }
    }
}

export {KettlerStatusBar};