const {createApp, ref, computed} = Vue

function formatDate(date_obj, sep = "-") {
    let month = date_obj.getMonth() + 1;
    let day = date_obj.getDate();
    return date_obj.getFullYear() + sep + (month < 10 ? "0" : "") + month + sep + (day < 10 ? "0" : "") + day
}

function formatHour(date_obj, sep = ":") {
    let hours = date_obj.getUTCHours();
    let minutes = date_obj.getUTCMinutes();
    return (hours < 10 ? "0" : "") + hours + sep + (minutes < 10 ? "0" : "") + minutes
}

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
            const original_start = new Date(JSON.parse(document.getElementById("original_start").value) * 1000);
            const DTSTART = ref(formatDate(original_start))
            const DTSTART_TIME = ref(formatHour(original_start))
            const rules = ref([])
            const dates = ref([])
            const weekdays = [gettext("Monday"), gettext("Tuesday"), gettext("Wednesday"), gettext("Thursday"), gettext("Friday"), gettext("Saturday"), gettext("Sunday")]
            const frequency_strings = [gettext("year"), gettext("month"), gettext("week"), gettext("day"), gettext("hour")]
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
                dates.value.push({date: formatDate(original_start), time: formatHour(original_start)});
            }

            async function removeDate(date) {
                dates.value.splice(dates.value.indexOf(date), 1)
            }

            async function changeFreq(rule, freq){
                rule.freq = freq
                rule.byweekday = []
                delete rule.bymonthday
                delete rule.bymonth
                delete rule.bysetpos
                delete rule.month_mode
            }

            function submitForm(event) {
                event.target.submit();
            }

            function isRuleValid(rule) {
                let isValid = true
                switch (rule.freq) {
                    case frequencies.WEEKLY:
                        isValid = isValid && rule.byweekday && rule.byweekday.length > 0
                        break
                    case frequencies.MONTHLY:
                        isValid = isValid && (rule.month_mode === "bymonthday" && rule.bymonthday || rule.month_mode === "bysetpos" && rule.bysetpos && rule.byweekday)
                        break
                    case frequencies.YEARLY:
                        isValid = isValid && (rule.month_mode === "bymonthday" && rule.bymonthday && rule.bymonth || rule.month_mode === "bysetpos" && rule.bysetpos && rule.byweekday && rule.bymonth)
                        break
                }

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
                        byweekday: rule.byweekday,
                        bymonthday: rule.month_mode === "bymonthday" ? rule.bymonthday : undefined,
                        bysetpos: rule.month_mode === "bysetpos" ? rule.bysetpos : undefined,
                        bymonth: rule.bymonth,
                        count: rule.end_mode === "COUNT" ? rule.count : undefined,
                        until: rule.end_mode === "UNTIL" && rule.until ? rrule.datetime(...rule.until.split("-"), formatHourOrZero(rule.UNTIL_TIME, pickHour)) : undefined,
                        tzid: Intl.DateTimeFormat().resolvedOptions().timeZone,
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
                    return formatDate(date) + " " + (date.getUTCHours() < 10 ? "0" : "") + date.getUTCHours() + ":" + (date.getUTCMinutes() < 10 ? "0" : "") + date.getUTCMinutes()
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
                submitForm,
                rrule_string,
                weekdays,
                months,
                dates,
                computed_dates,
                pickHour,
                frequencies,
                frequency_strings,
                changeFreq,
                isRuleValid,
            }
        }, delimiters: ['[[', ']]']
    }).mount('#vue_app');
});
