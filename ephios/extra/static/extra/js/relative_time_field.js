document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".relative-time-widget").forEach((wrapper) => {
        const select = wrapper.querySelector(".field-0 select");
        const day = wrapper.querySelector(".field-1 input");
        const month = wrapper.querySelector(".field-2 input");
        const years = wrapper.querySelector(".field-3 input");

        const all_fields = [day, month, years];

        const relative_time_map = {
            0: [], // no_expiration
            1: [years], // after_x_years
            2: [day, month, years], // at_xy_after_z_years
        };

        function updateVisibility() {
            const val = parseInt(select.value);
            const show = relative_time_map[val] || [];

            all_fields.forEach((field) => {
                if (!field) return;
                field.parentElement.style.display = show.includes(field) ? "" : "none";
            });
        }

        select.addEventListener("change", updateVisibility);
        updateVisibility();
    })
})