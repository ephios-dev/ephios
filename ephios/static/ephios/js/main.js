function handleForms(elem) {
    // Configure the subtree specified by the root elem (jquery object) for use
    // with the various JS libs
    elem.find('[data-toggle="tooltip"]').tooltip();
    elem.find(".django-select2").djangoSelect2()
    elem.find("[data-formset]").formset({
        animateForms: true,
        reorderMode: 'dom',
    }).on("formAdded", "div", function (event) {
        handleForms($(event.target));
    });
}

$(document).ready(function () {
    // Configure all prerendered Forms
    handleForms($(document));

    // Used for disposition TODO: move to plugin specific JS!
    $("[data-drop-to-state]").each(function (index, elem) {
        Sortable.create(elem, {
            group: "participations",
            sort: false,
            draggable: ".draggable",
            emptyInsertThreshold: 50,
            animation: 150,
            easing: "cubic-bezier(1, 0, 0, 1)",
            onAdd: function (event) {
                const newState = $(event.target).data("drop-to-state");
                $(event.item).find(".state-input").val(newState);
            },
        });
    });

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
    html = '<div class="alert alert-' + cls + ' alert-dismissible fade show" role="alert">' + message + `
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>`;
    $("#messages").append(html);
}