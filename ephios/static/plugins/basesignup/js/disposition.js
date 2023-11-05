$(document).ready(function () {
    $("#id_user").djangoSelect2({
        theme: "bootstrap-5",
        insertTag: function (data, tag) {
            // Insert the tag at the end of the results
            if (data.length === 0) {
                data.push(tag);
            }
        },
        createTag: function (params) {
            return {
                id: params.term,
                text: gettext("Create \"{userName}\" as placeholder").replace("{userName}", params.term),
                userName: params.term,
                guestUser: true
            }
        }
    });

    function handleDispositionForm($form, state, instant) {
        $form.find("[data-show-for-state]").each((index, el) => {
            el = $(el);
            if (state && el.attr("data-show-for-state").split(",").includes(state.toString())) {
                el.slideDown();
            } else if (!instant) {
                el.slideUp();
            } else {
                el.hide();
            }
        });
    }

    function addForm(formset, form, newIndex, $spinner) {
        // updating the formset is adapted from `addForm` in formset.js
        formset.$managementForm('TOTAL_FORMS').val(newIndex + 1);
        formset.$managementForm('INITIAL_FORMS').val(newIndex + 1);

        // fade spinner into prepared form
        const $newFormFragment = $($.parseHTML(form)).hide();
        handleDispositionForm($newFormFragment, false, true);
        $spinner.fadeOut("fast", function () {
            $(this).replaceWith($newFormFragment);
            handleForms($newFormFragment);
            $newFormFragment.fadeIn("fast");
        });

        // register form with formset
        const $newForm = $newFormFragment.filter(formset.opts.form);
        formset.bindForm($newForm, newIndex);
    }

    function showSpinner(spawn) {
        // Put a spinner. Height 55px is what the default template produces for the card about to be loaded.
        const spinnerHtml = `<div class="list-group-item">
                                     <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true">
                                 </div></div>`;
        const $spinner = $($.parseHTML(spinnerHtml)).hide().css("height", "55px");
        spawn.append($spinner);
        $spinner.slideDown("fast");
        return $spinner;
    }

    $("[data-drop-to-state]").each(function (index, elem) {
        const newState = $(elem).data("drop-to-state");
        Sortable.create(elem, {
            group: {
                name: "participations",
                put: !$(elem).hasClass("sortable-reject-put")
            },
            sort: true,
            draggable: ".draggable",
            filter: ".do-not-drag",
            preventOnFilter: false,
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

    $("select#id_user[form='add-user-form']").on('select2:close', function (e) {
        // clear select2
        setTimeout(() => {
            $("#id_user").empty().trigger('change');
        });
    });

    $("select#id_user[form='add-user-form']").on('select2:select', function (e) {
        const spawn = $("[data-formset-spawn]");
        const formset = $('#participations-form').formset('getOrCreate');

        // handle guest users
        if (e.params.data.guestUser) {
            const $spinner = showSpinner(spawn);
            const newIndex = $('#participations-form').formset('getOrCreate').totalFormCount();
            $.ajax({
                url: $("#" + $(this)[0].form.id).data("placeholder-url"),
                type: "post",
                dataType: "html",
                data: {
                    "display_name": e.params.data.userName,
                    "new_index": newIndex,
                    "csrfmiddlewaretoken": getCookie("csrftoken"),
                },
                timeout: 10000,
                success: (data) => addForm(formset, data, newIndex, $spinner),
                error: () => {
                    $spinner.slideUp();
                    $spinner.remove();
                    alert("Connection failed.");
                },
            })
            return;
        }

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
                // already exists, move back to spawn, undelete and show it.
                spawn.append(participation.detach());
                deleteCheckbox.attr("checked", false).change();
                participation.slideDown();
            } else {
                // already visible. Move there and highlight it.
                participation[0].scrollIntoView({behavior: "smooth", block: "end"});
                participation.focus();
                participation.addClass("list-group-item-info");
                setTimeout(() => {
                    participation.removeClass("list-group-item-info")
                }, 2000);
            }
        } else {
            // We want to load using ajax.
            const $spinner = showSpinner(spawn)

            // get the new form from the server
            const addUserForm = $("#" + $(this)[0].form.id);
            const newIndex = formset.totalFormCount();
            addUserForm.find('[name=new_index]').val(newIndex);
            $.ajax({
                url: addUserForm.attr("action"),
                type: 'post',
                dataType: 'html',
                data: addUserForm.serialize(),
                timeout: 10000,
                success: (data) => addForm(formset, data, newIndex, $spinner),
                error: () => {
                    $spinner.slideUp();
                    $spinner.remove();
                    alert("Connection failed.");
                }
            });
        }
    });

});