function handleForms(elem) {
    // Configure the subtree specified by the root elem (jquery object) for use
    // with the various JS libs
    elem.find('[data-bs-toggle="tooltip"]').tooltip();

    // https://getbootstrap.com/docs/5.0/components/popovers/
    elem.find('[data-bs-toggle="popover"]').each((idx, el) => {
        new bootstrap.Popover(el, {
            html: true,
            content: function () {
                return $("html").find(el.getAttribute("data-bs-content-ref")).html();
            },
            title: function () {
                return $("html").find(el.getAttribute("data-bs-title-ref")).html();
            }
        });
    });

    elem.find(".django-select2").djangoSelect2({
        theme: "bootstrap-5"
    });
    elem.find("[data-formset]").formset({
        animateForms: true,
        reorderMode: 'dom',
    }).on("prepareNewFormFragment", "[data-formset-form]", function (event) {
        // Handle any forms that were added to the template with this custom event and
        // not 'formAdded' as that would be called after animation leading to
        // the slideDown animation not using the correct height
        handleForms($(event.target));
    });
    elem.find(".action-navigate-back").click(function () {
        window.history.back();
    });
    elem.find(".select-auto-width").each((index, select) => {
        // https://stackoverflow.com/a/49693251/4837975
        select.addEventListener('change', function () {
            const span = document.createElement('span');
            const option = select.options[select.selectedIndex];
            if (option) {
                span.textContent = option.textContent;
                const optionStyles = getComputedStyle(option);
                span.style.fontFamily = optionStyles.fontFamily;
                span.style.fontStyle = optionStyles.fontStyle;
                span.style.fontWeight = optionStyles.fontWeight;
                span.style.fontSize = optionStyles.fontSize;
            }
            document.body.appendChild(span);
            select.style.width = `${span.offsetWidth + 45}px`;
            document.body.removeChild(span);
        });
        // Trigger for the first time
        select.dispatchEvent(new Event('change'));
    });
    elem.find("[data-ajax-replace-select]").each((index, div) => {
        /*
         * In a htmx style, use "data-ajax-replace-url" on a div to have the content be replaced
         * by the content returned. The div's inner html will be replaced with the fetched html
         * and handleForms will be called on the new content.
         * The url should contain "SELECT_VALUE" which will be replaced with the value of the select input.
         */
        const select = document.getElementById(div.getAttribute("data-ajax-replace-select"));
        const fetchAndReplace = () => {
            const url = div.getAttribute("data-ajax-replace-url").replace("SELECT_VALUE", select.value);
            fetch(url).then(response => response.text()).then(html => {
                // store every form input value to restore it after replacing the form
                const oldFormInputs = div.querySelectorAll("input, select, textarea");
                const formValues = {};
                oldFormInputs.forEach(input => {
                        // avoid hidden inputs as that might interfere with csrf/formset management
                        // beware of selects not having a type attribute
                        if (input.type !== "hidden") {
                            // TODO breaks with select2?!
                            formValues[input.name] = input.value;
                        }
                    }
                );
                div.innerHTML = html;
                const newFormInputs = div.querySelectorAll("input, select, textarea");
                newFormInputs.forEach(input => {
                    if (formValues[input.name]) {
                        input.value = formValues[input.name];
                    }
                });
                handleForms($(div));
            });
        };
        select.addEventListener("change", fetchAndReplace);
        if (div.innerHTML.trim() === "") {
            fetchAndReplace();
        }
    });
}

$(document).ready(function () {
    // Configure all prerendered Forms
    handleForms($(document));

    var recurrenceFields = document.querySelectorAll('.recurrence-widget');
    Array.prototype.forEach.call(recurrenceFields, function (field, index) {
        new recurrence.widget.Widget(field.id, {});
    });

    $('#checkall').change(function () {
        $('.cb-element').prop('checked', this.checked);
    });

    $('.cb-element').change(function () {
        if ($('.cb-element:checked').length === $('.cb-element').length) {
            $('#checkall').prop('checked', true);
        } else {
            $('#checkall').prop('checked', false);
        }
    });

    // Blur the view when loading a new page as PWA
    // https://stackoverflow.com/a/41749865
    if (navigator.standalone || window.matchMedia('(display-mode: standalone)').matches) {
        $(window).on('beforeunload', function () {
            $('.blur-on-unload').addClass("unloading");
            $('#unloading-spinner').removeClass("d-none");
        });
    }
    // when hitting "back" button in browser, the page is not reloaded so we need to remove the blur manually
    window.addEventListener('pageshow', function (event) {
        $('.blur-on-unload').removeClass("unloading");
        $('#unloading-spinner').addClass("d-none");
    });

    if ($("body").data("pwa-network") === "offline") {
        // disable all forms and post buttons
        $("form").find("input, [type='submit'], select, textarea").prop("disabled", true);
        // display a warning that the page is outdated
        $("#messages").empty();
        let time = document.querySelector("meta[name='created']").getAttribute('content');
        time = new Date(time).toLocaleString(document.querySelector("html").getAttribute('lang'));
        message(
            "warning",
            gettext("You are currently offline and seeing the content as it was on {time}.").replace("{time}", time)
            + " (" + gettext("experimental") + ")", 0
        );
    }

    // Initialize the service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/serviceworker.js', {
            scope: '/'
        }).then(function (registration) {
            console.log('ephios: ServiceWorker registration successful with scope: ', registration.scope);
            const logoutLink = document.getElementById("logout-link");
            if (logoutLink) {
                logoutLink.addEventListener("click", (event) => {
                    // We use a new cache for every new user and set of permissions, but for that to be secure
                    // when logging out, that requires loading another ephios page to install a new service worker
                    // --> so on logout, we explicitly tell the serviceworker to clear its cache
                    registration.active.postMessage("logout");
                });
            }
        }, function (err) {
            console.log('ephios: ServiceWorker registration failed: ', err);
        });
    }

})

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function message(cls, message, timeout) {
    html = '<div class="alert alert-' + cls + ' alert-dismissible show" role="alert">' + message + `
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>`;
    $("#messages").append(html);
}