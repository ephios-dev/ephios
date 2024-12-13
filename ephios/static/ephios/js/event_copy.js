const {createApp, ref, computed} = Vue

function formatHourOrZero(time_string, pickHour=false) {
    if (time_string && pickHour) {
        return [time_string.slice(0,2), time_string.slice(3,5), 0]
    }
    return [0, 0, 0]
}

document.addEventListener('DOMContentLoaded', (event) => {
    createApp({
        setup() {
            const pickHour = JSON.parse(document.getElementById("pick_hour").value);
            const original_start = document.getElementById("original_start").value
            const original_date = original_start.slice(0, 10)
            const original_time = original_start.slice(11, 19)
            const DTSTART = ref(original_date)
            const DTSTART_TIME = ref(pickHour ? original_time : "")
            const rules = ref([])
            const dates = ref([])
            const weekdays = [gettext("Monday"), gettext("Tuesday"), gettext("Wednesday"), gettext("Thursday"), gettext("Friday"), gettext("Saturday"), gettext("Sunday")]
            const frequency_strings = [gettext("years"), gettext("months"), gettext("weeks"), gettext("days"), gettext("hours")]
            const frequencies = rrule.Frequency
            const months = [
                {id: 1, short: gettext("Jan"), long: gettext("January")},
                {id: 2, short: gettext("Feb"), long: gettext("February")},
                {id: 3, short: gettext("Mar"), long: gettext("March")},
                {id: 4, short: gettext("Apr"), long: gettext("April")},
                {id: 5, short: gettext("May"), long: gettext("May")},
                {id: 6, short: gettext("Jun"), long: gettext("June")},
                {id: 7, short: gettext("Jul"), long: gettext("July")},
                {id: 8, short: gettext("Aug"), long: gettext("August")},
                {id: 9, short: gettext("Sep"), long: gettext("September")},
                {id: 10, short: gettext("Oct"), long: gettext("October")},
                {id: 11, short: gettext("Nov"), long: gettext("November")},
                {id: 12, short: gettext("Dec"), long: gettext("December")}
            ]

            async function addRule() {
                rules.value.push({freq: rrule.RRule.WEEKLY, interval: 1, byweekday: []})
            }

            async function removeRule(rule) {
                rules.value.splice(rules.value.indexOf(rule), 1)
            }

            async function addDate() {
                dates.value.push({date: original_date, time: original_time});
            }

            async function removeDate(date) {
                dates.value.splice(dates.value.indexOf(date), 1)
            }

            async function freqChanged(rule){
                rule.byweekday = rule.freq >= rrule.Frequency.WEEKLY ? [] : 0;
                rule.bysetpos = 1;
                rule.bymonthday = 1;
                rule.bymonth = 1;
                delete rule.month_mode;
            }

            function isRuleValid(rule) {
                let isValid = true
                switch (rule.freq) {
                    case frequencies.WEEKLY:
                        isValid = isValid && rule.byweekday && rule.byweekday.length > 0
                        break
                    case frequencies.MONTHLY:
                        isValid = isValid && (rule.month_mode === "bymonthday" && rule.bymonthday || rule.month_mode === "bysetpos" && rule.bysetpos && rule.byweekday !== "")
                        break
                    case frequencies.YEARLY:
                        isValid = isValid && (rule.month_mode === "bymonthday" && rule.bymonthday && rule.bymonth || rule.month_mode === "bysetpos" && rule.bysetpos && rule.byweekday !== "" && rule.bymonth)
                        break
                }

                // DTSTART set
                isValid = isValid && DTSTART.value

                // end date set
                isValid = isValid && (rule.end_mode === "COUNT" && rule.count && rule.count > 0 || rule.end_mode === "UNTIL" && rule.until)

                return isValid
            }

            const rrule_set = computed(() => {
                let set = new rrule.RRuleSet()
                rules.value.forEach(rule => {
                    if (!isRuleValid(rule)) {
                        return
                    }
                    set.rrule(new rrule.RRule({
                        freq: rule.freq,
                        interval: rule.interval,
                        dtstart: rrule.datetime(...DTSTART.value.split("-"), ...formatHourOrZero(DTSTART_TIME.value, pickHour)),
                        byweekday: rule.month_mode === "bysetpos" || rule.freq === rrule.Frequency.WEEKLY ? rule.byweekday : undefined,
                        bymonthday: rule.month_mode === "bymonthday" ? rule.bymonthday : undefined,
                        bysetpos: rule.month_mode === "bysetpos" ? rule.bysetpos : undefined,
                        bymonth: rule.freq === rrule.Frequency.YEARLY ? rule.bymonth : undefined,
                        count: rule.end_mode === "COUNT" ? rule.count : undefined,
                        until: rule.end_mode === "UNTIL" && rule.until ? rrule.datetime(...rule.until.split("-"), ...formatHourOrZero(rule.UNTIL_TIME, pickHour)) : undefined,
                    }))
                })
                dates.value.forEach(date => {
                    if (date.date && (!pickHour || date.time)) {
                        set.rdate(rrule.datetime(...date.date.split("-"), ...formatHourOrZero(date.time, pickHour)))
                    }
                })
                return set
            })

            const computed_dates = computed(() => {
                return rrule_set ? rrule_set.value.all().map(date => {
                    return new Intl.DateTimeFormat('de-DE', {
                        dateStyle: 'full',
                        timeStyle: pickHour ? 'short' : undefined,
                        timeZone: "UTC",
                      }).format(date)
                }): []
            })

            const rrule_string = computed(() => {
                return rrule_set ? rrule_set.value.toString() : ""
            })

            return {
                rules,
                DTSTART,
                DTSTART_TIME,
                addRule,
                removeRule,
                addDate,
                removeDate,
                rrule_string,
                weekdays,
                months,
                dates,
                computed_dates,
                pickHour,
                frequencies,
                frequency_strings,
                freqChanged,
                isRuleValid,
            }
        }, delimiters: ['[[', ']]']
    }).mount('#vue_app');
});
