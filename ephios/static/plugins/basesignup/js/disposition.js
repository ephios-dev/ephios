$(document).ready(function () {
    function handleDispositionForm($form, state, instant) {
        $form.find("[data-show-for-state]").each((index, el) => {
            el = $(el);
            if (el.attr("data-show-for-state").split(",").includes(state.toString())) {
                el.slideDown();
            } else if (!instant) {
                el.slideUp();
            } else {
                el.fadeOut(0);
            }
        });
    }

    $("[data-drop-to-state]").each(function (index, elem) {
        const newState = $(elem).data("drop-to-state");
        Sortable.create(elem, {
            group: "participations",
            sort: true,
            draggable: ".draggable",
            emptyInsertThreshold: 20,
            fallbackTolerance: 5,
            animation: 150,
            easing: "cubic-bezier(1, 0, 0, 1)",
            // scrolling
            scrollSensitivity: 150,
            scrollSpeed: 15,
            // set state
            onAdd: (event) => {
                $(event.item).find(".state-input").val(newState);
                handleDispositionForm($(event.item), newState, false);
            },
        });
        handleDispositionForm($(elem), newState, true);
    });

    $("select#id_user[form='add-user-form']").on('select2:close', function () {
        // clear select2
        const userSelect = $(this);
        setTimeout(() => {
            userSelect.val(null).change()
        });

        const spawn = $("[data-formset-spawn]");
        const formset = $('#participation-form').formset('getOrCreate');
        // look for existing form with that participation
        const userId = $(this).val();
        if (!userId) {
            return;
        }

        const participation = $('[data-participant-id=' + userId + ']');
        if (participation.length) {
            // we already have that card
            const prefix = formset.extractPrefix(participation);
            const deleteCheckbox = participation.find('[name=' + prefix + '-DELETE]');
            if (deleteCheckbox.attr("checked")) {
                // was marked for deletion, so revert that.
                participation.attr("data-formset-created-at-runtime", true); // so formset.js decides to slideDown() it
                deleteCheckbox.attr("checked", false).change();
            }
            // now visible. Move it to here.
            $([document.documentElement, document.body]).animate({
                scrollTop: participation.offset().top - 200
            }, 1000);
            participation.focus();
            participation.addClass("list-group-item-info");
            setTimeout(() => {
                participation.removeClass("list-group-item-info")
            }, 2000);
        } else {
            // get the new form from the server
            const addUserForm = $("#" + $(this)[0].form.id);
            $.ajax({
                url: addUserForm.attr("action"),
                type: 'post',
                dataType: 'html',
                data: addUserForm.serialize(),
                success: function (data) {
                    // adapted from addForm from formset.js
                    // update management form
                    const newIndex = formset.totalFormCount() + 1;
                    formset.$managementForm('TOTAL_FORMS').val(newIndex);
                    formset.$managementForm('INITIAL_FORMS').val(newIndex);

                    // insert html
                    const $newFormFragment = $($.parseHTML(data));
                    spawn.append($newFormFragment);

                    var $newForm = $newFormFragment.filter(formset.opts.form);
                    formset.bindForm($newForm, newIndex);
                    $newForm.attr("data-formset-created-at-runtime", "true");
                }
            });
        }
    });

});