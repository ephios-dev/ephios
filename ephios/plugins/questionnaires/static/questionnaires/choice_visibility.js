function updateChoicesVisibility() {
    let typeInput = document.getElementById("id_type");
    let choices = $("#choices-formset");

    if (typeInput.value === "text") {
        choices.slideUp();
    } else {
        choices.slideDown();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    updateChoicesVisibility();
    document.getElementById("id_type").addEventListener("change", updateChoicesVisibility);
});
