const {createApp, ref, computed} = Vue

document.addEventListener('DOMContentLoaded', (event) => {
    createApp({
        setup() {
            const DTSTART = ref(new Date())
            const rules = ref([{
                freq: "WEEKLY", interval: 1, BYWEEKDAY: []
            }])
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

            const rrule_string = computed(() => {
                return "DTSTART:" + DTSTART.value.toISOString().replace("-", "") + "\n" + rules.value.map(rule => {
                    return "FREQ=" + rule.freq + ";INTERVAL=" + rule.interval + ";" //+ rule.BYWEEKDAY.join(",")
                }).join(";")
            })

            return {
                rules, DTSTART, addRule, removeRule, rrule_string, weekdays, months,
            }
        }, delimiters: ['[[', ']]']
    }).mount('#recurrence');
});
