function setChoicesVisibility() {
    let typeInput = document.getElementById("id_type");
    let choices = document.getElementById("choices-formset");

    choices.style.display = typeInput.value === "text" ? "none" : "initial";
}

document.addEventListener("DOMContentLoaded", () => {
    setChoicesVisibility();
    document.getElementById("id_type").addEventListener("change", setChoicesVisibility);
});
