const {createApp, ref, computed} = Vue

function formatDate(date_obj, sep="-") {
    let month = date_obj.getMonth() + 1;
    let day = date_obj.getDate() + 1;
    return date_obj.getFullYear() + sep + (month < 10 ? "0" : "") + month + sep + (day < 10 ? "0" : "") + day
}

document.addEventListener('DOMContentLoaded', (event) => {
    createApp({
        setup() {
            const DTSTART = ref(formatDate(new Date()))
            const rules = ref([])
            const dates = ref([])
            const weekdays = [{id: "MO", short: "Mon", long: "Monday"}, {
                id: "TU", short: "Tue", long: "Tuesday"
            }, {id: "WE", short: "Wed", long: "Wednesday"}, {id: "TH", short: "Thu", long: "Thursday"}, {
                id: "FR", short: "Fri", long: "Friday"
            }, {id: "SA", short: "Sat", long: "Saturday"}, {id: "SU", short: "Sun", long: "Sunday"}]
            const months = [{id: 1, short: "Jan", long: "January"}, {id: 2, short: "Feb", long: "February"}, {
                id: 3, short: "Mar", long: "March"
            }, {id: 4, short: "Apr", long: "April"}, {id: 5, short: "May", long: "May"}, {
                id: 6, short: "Jun", long: "June"
            }, {id: 7, short: "Jul", long: "July"}, {id: 8, short: "Aug", long: "August"}, {
                id: 9, short: "Sep", long: "September"
            }, {id: 10, short: "Oct", long: "October"}, {id: 11, short: "Nov", long: "November"}, {
                id: 12, short: "Dec", long: "December"
            }]

            async function addRule() {
                rules.value.push({
                    freq: "WEEKLY", interval: 1, BYWEEKDAY: [],
                })
            }

            async function removeRule(rule) {
                rules.value.splice(rules.value.indexOf(rule), 1)
            }

             async function addDate() {
                dates.value.push({date: ""});
            }

            async function removeDate(date) {
                dates.value.splice(dates.value.indexOf(date), 1)
            }

            function submitForm(event) {
                event.target.submit();
            }

            const computed_dates = computed(() => {
                return fetch("http://localhost:8000/extra/rruleoccurrence/", {
                    method: "POST", body: JSON.stringify({
                        recurrence_string: rrule_string.value,
                    }), headers: {"X-CSRFToken": getCookie("csrftoken")},
                }).then(response => response.json());
            })

            const rrule_string = computed(() => {
                return "DTSTART;TZID=" + Intl.DateTimeFormat().resolvedOptions().timeZone + ":" + formatDate(new Date(DTSTART.value), "") + "T000000\n" + rules.value.map(rule => {
                    let rule_str = "FREQ=" + rule.freq + ";INTERVAL=" + rule.interval;
                    switch (rule.freq) {
                        case "WEEKLY":
                            rule_str += ";BYWEEKDAY=" + (Array.isArray(rule.BYWEEKDAY) ? rule.BYWEEKDAY.join(",") : rule.BYWEEKDAY);
                            break;
                        case "MONTHLY":
                            if (rule.month_mode === "BYMONTHDAY") {
                                rule_str += ";BYMONTHDAY=" + rule.BYMONTHDAY
                            } else {
                                rule_str += ";BYWEEKDAY=" + rule.BYWEEKDAY + ";BYSETPOS=" + rule.BYSETPOS
                            }
                            break;
                        case "YEARLY":
                            if (rule.year_mode === "BYMONTHDAY") {
                                rule_str += ";BYMONTHDAY=" + rule.BYMONTHDAY + ";BYMONTH=" + rule.BYMONTH
                            } else {
                                rule_str += ";BYWEEKDAY=" + rule.BYWEEKDAY + ";BYSETPOS=" + rule.BYSETPOS + ";BYMONTH=" + rule.BYMONTH
                            }
                    }
                    if (rule.end_mode === "COUNT") {
                        rule_str += ";COUNT=" + rule.COUNT
                    } else if (rule.end_mode === "UNTIL") {
                        rule_str += ";UNTIL=" + rule.UNTIL
                    }
                    return rule_str;
                }).join("\n") + dates.value.map(date => {
                    return "RDATE;TZID=" + Intl.DateTimeFormat().resolvedOptions().timeZone + ":" + formatDate(new Date(date.date), "") + "T000000"
                }).join("\n")
            })

            return {
                rules, DTSTART, addRule, removeRule, addDate, removeDate, submitForm, rrule_string, weekdays, months, dates, computed_dates,
            }
        }, delimiters: ['[[', ']]']
    }).mount('#recurrence');
});
