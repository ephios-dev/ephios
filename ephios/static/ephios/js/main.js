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
            console.log('django-pwa: ServiceWorker registration successful with scope: ', registration.scope);
        }, function (err) {
            console.log('django-pwa: ServiceWorker registration failed: ', err);
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