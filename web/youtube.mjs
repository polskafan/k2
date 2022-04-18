class EffortLevel {
    constructor(effort, start, end, duration) {
        this.effort = effort;
        this.start = start;
        this.end = end;
        this.duration = duration;
    }

    getProgress(time) {
        return Math.max(0, Math.min(1, (time - this.start) / this.duration));
    }

    isCurrent(time) {
        if (this.end === null) {
            return this.start < time;
        } else {
            return this.start < time && time < this.end;
        }
    }

    getLabel() {
        switch(this.effort) {
            case "start":
                return "<span>Start</span>";
            case "end":
                return "<span>End</span>";
            default:
                return `<span>${this.duration}s</span><span>Level ${this.effort}</span>`;
        }
    }
}

class YouTubeTrianer {
    constructor(YT, playerSelector, statusBarSelector, k2, workout) {
        this.YT = YT;

        this.player = new this.YT.Player(playerSelector, {
            videoId: workout.videoId,
            width: '100%',
            height: '100%',
            events: {
                'onStateChange': this.onPlayerStateChange.bind(this)
            }
        })

        this.statusElement = document.querySelector(statusBarSelector);

        this.currentEffortLevel = 0;
        this.k2 = k2;
        this.effortLevels = this.getLevels(workout);
        this.timer = null;
        this.onStatus(0);
    }

    getLevels(workout) {
        let cumulatedTime = workout.start;
        let levels = workout.levels.map((level) => {
            let el = new EffortLevel(level.effort, cumulatedTime, cumulatedTime + level.duration, level.duration);
            cumulatedTime += level.duration;
            return el;
        });

        return [
            new EffortLevel("start", 0, workout.start, workout.start),
            ...levels,
            new EffortLevel("end", cumulatedTime, null,null)];
    }

    onPlayerStateChange(event) {
        switch(event.data) {
            case this.YT.PlayerState.PLAYING:
                if (this.timer === null) {
                    this.timer = setInterval(() => {
                        let effortLevel = this.getEffortAtTime(this.player.playerInfo.currentTime);
                        if (effortLevel !== this.currentEffortLevel) {
                            if (this.k2 !== undefined) {
                                this.k2.setEffortLevel(effortLevel.effort);
                                this.currentEffortLevel = effortLevel;
                            }
                        }
                        this.onStatus(this.player.playerInfo.currentTime);
                    }, 500);
                }
                break;

            default:
                clearTimeout(this.timer);
                this.timer = null;
                break;
        }
    }

    getEffortAtTime(time) {
        return this.effortLevels.find(element => element.isCurrent(time));
    }

    onStatus(time) {
        // render one line per level
        let levels = this.effortLevels.map((level) => {
            if(level.isCurrent(time)) {
                return `<div class="progress active">
<div class="label">${level.getLabel()}</div>
<span class="value" style="width: ${level.getProgress(time)*100}%;"></span>
</div>`;
            } else {
                return `<div class="progress inactive">
<div class="label">${level.getLabel()}</div>
<span class="value" style="width: ${level.getProgress(time)*100}%;"></span></div>`;
            }
        })
        this.statusElement.innerHTML = levels.join("\n");
    }
}

export {YouTubeTrianer};