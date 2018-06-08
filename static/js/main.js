document.addEventListener("DOMContentLoaded", function() {

    /* Initialize tooltips */
    $('[data-toggle="tooltip"]').tooltip();

    /* This block disables the submit button when a result has only been partially entered: ie - one team's goals, but not the other */
    let numberfields = $("input[type='number']")
    let invalid_scores = []
    $(numberfields).on("input", function(e) {
        let sibling = $(this).parent().siblings("td").children("input[type='number']")
        /* If either inputs are empty, disable the button and show error message */
        if ($(sibling).val() == '' || $(this).val() == '') {
            $("#predict_scores").prop('disabled', true)
            $("#form-disabled-error").removeClass("d-none").addClass("d-block")

            /* Check which of the inputs are empty, and check whether this input is already in the invalid_scores array.
               If empty and not in the invalid_scores array, add it */
            if (isEmpty($(this)) && !existsInArray($(this), invalid_scores))
                invalid_scores.push($(this).attr("id"))
            if (isEmpty($(sibling)) && !existsInArray($(sibling), invalid_scores))
                invalid_scores.push($(sibling).attr("id"))
        } else {
            /* Check which of the inputs are NOT empty, and remove from invalid_scores array if they exist in the array */
            if (!isEmpty($(this))) {
                let index = invalid_scores.indexOf($(this).attr('id'))
                if (index >= 0)
                    invalid_scores.splice(index, 1)
            }
            if (!isEmpty($(sibling))) {
                let index2 = invalid_scores.indexOf($(sibling).attr('id'))
                if (index2 >= 0)
                    invalid_scores.splice(index2, 1)
            }
            /* If there are no invalid scores, re-enable the submit button and remove the error message */
            if (invalid_scores.length == 0) {
                $("#predict_scores").prop('disabled', false)
                $("#form-disabled-error").removeClass("d-block").addClass("d-none")
            }
        }
    })

    /* Function that determines whether the given element is empty or not */
    isEmpty = (element) => element.val() == ''

    /* Function that determines whether an element is already present in an array or not */
    existsInArray = (element, array) => array.indexOf(element.attr('id')) >= 0

});