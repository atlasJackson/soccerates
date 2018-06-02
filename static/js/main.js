document.addEventListener("DOMContentLoaded", function() {

    /* This block disables the submit button when a result has only been partially entered: ie - one team's goals, but not the other */
    let numberfields = $("input[type='number']")
    let invalid_scores = []
    $(numberfields).on("input", function(e) {
        let sibling = $(this).parent().siblings("td").children("input[type='number']")
        if ($(sibling).val() == '' || $(this).val() == '') {
            $("#predict_scores").prop('disabled', true)
            $("#form-disabled-error").removeClass("d-none").addClass("d-block")
            if (isEmpty($(this)) && !existsInArray($(this), invalid_scores))
                invalid_scores.push($(this).attr("id"))
            if (isEmpty($(sibling)) && !existsInArray($(sibling), invalid_scores))
                invalid_scores.push($(sibling).attr("id"))
        } else {
            if (!isEmpty($(this))) {
                let index = invalid_scores.indexOf($(this).attr('id'))
                if (index >= 0)
                    invalid_scores.splice(index, 1)
                let index2 = invalid_scores.indexOf($(sibling).attr('id'))
                if (index2 >= 0)
                    invalid_scores.splice(index2, 1)
            }
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