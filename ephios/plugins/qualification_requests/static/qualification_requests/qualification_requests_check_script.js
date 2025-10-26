const calculateExpirationURL = "/api/qualifications/default-expiration-date/calculate/"

document.addEventListener("DOMContentLoaded", () => {
    const qualificationField = document.querySelector("#id_qualification");
    const qualificationDateField = document.querySelector("#id_qualification_date");
    const expirationField = document.querySelector("#id_expiration_date");
    const errorContainer = document.createElement("div");
    errorContainer.classList.add("text-danger", "mt-1");
    expirationField.parentNode.appendChild(errorContainer);

    async function updateExpirationDate() {
        const qualification = qualificationField.value;
        const qualification_date = qualificationDateField.value;
        errorContainer.textContent = "";

        if(!qualification || !qualification_date){
            expirationField.value = "";
            return;
        }

        try{
            const response = await fetch(
                `${calculateExpirationURL}?qualification=${qualification}&qualification_date=${qualification_date}`
            );

            const data = await response.json();

            if(!response.ok || data.error){
                expirationField.value = "";
                errorContainer.textContent = data.error || "Unknown error.";
                return;
            }

            expirationField.value = data.expiration_date || "";
        } catch (err){
            expirationField.value = "";
            errorContainer.textContent = "Network error: " + err.message;
        }
    }

    function observeField(field){
        field.addEventListener("input", updateExpirationDate)
        field.addEventListener("change", updateExpirationDate)
    }

    observeField(qualificationDateField);

    if(window.jQuery && jQuery.fn.select2){
        jQuery('#id_qualification').on('select2:select select2:clear', updateExpirationDate);
    }else{
        const observer = new MutationObserver(() => updateExpirationDate());
        observer.observe(qualificationField, { attributes: true, attributeFilter: ["value"] });
    }

    updateExpirationDate();
})