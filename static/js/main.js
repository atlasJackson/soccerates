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

    /* Function that changes the user profile. */
    $(".user-profile").on("click", "#user-profile-image", function() {
        $("#picture-upload").click();
    });
    $("#picture-upload").on("change", function() {
        $("#profile-image-form").submit();
    });

    /* LEADERBOARDS */
    $("#join-boards").on("click", function() {
        var link = $(this);
        $(".all-boards").slideToggle(300, function () {
            if ($(this).is(':visible')) {
                 link.text('Hide Leaderboards');                
            } else {
                 link.text('Show Leaderboards');                
            }
        });
    });

    /* Displays password fields if private leadderboard is selected in the create_lb form */
    if ($(".create_private").is(':checked')) {
        $(".create-lb-pass").show();             
    } else {            
        $(".create-lb-pass").hide();
    } 
    $(".create_private").on("click", function(e) {
       
        $(".create-lb-pass").slideToggle(200);
    });

    /* Buttons to join and leave leaderboards */
    $(".board-content").on("click", "#join-button", function(e) {

        e.preventDefault();
        buttonJoinLeave($(this), "join_leaderboard/");
    });
    $(".board-content").on("click", "#leave-button", function(e) {

        e.preventDefault();
        buttonJoinLeave($(this), "leave_leaderboard/");
    });

    /* Performs AJAX request to paginate the leaderboard options based on the page clicked */
    $(".all-boards").on("click", ".link-pagination", function(e) {
        e.preventDefault()
        let page = $(this).attr("href")
        page = page.substr(page.length - 1)
        let searchTerm = $("#board-searchbox").val()
        var postRequest = $.post("/ajax/leaderboards/get_page", {'page': page, 'search_term':searchTerm})
        postRequest.done(function(data) {
            $(".all-boards").html(data)
            $("#board-searchbox").val(searchTerm)
        });
    })

    $(".all-boards").on("click", "#board-searchbtn", function(e) {
        let searchTerm = $("#board-searchbox").val()
        var postRequest = $.post("/ajax/leaderboards/search", {'search_term': searchTerm})
        postRequest.done(function(data) {
            $(".all-boards").html(data)
            $("#board-searchbox").val(searchTerm)
            $("#board-searchbox").focus()
        });
    })

    $(".all-boards").on("click", "#clearsearch", function(e) {
        let searchTerm = ''
        var postRequest = $.post("/ajax/leaderboards/search", {'search_term': searchTerm})
        postRequest.done(function(data) {
            $(".all-boards").html(data)
        });
    })

});

/* Function that implements the joining and leaving of leaderboards using ajax. */
function buttonJoinLeave(button, urlLink) {
    $.ajax({
        type: "POST",
        url: urlLink,
        data: {
            "leaderboard": button.data("leaderboard"),
            csrfmiddlewaretoken: button.data("csrf_token"),
        },
        dataType: "json",
        success: function(data) {
            if (data.board_empty) {
                alert("As you were the last user in this board, the board will be deleted.");
                window.location.replace("/");

            } else if (data.left_private_board) {
                window.location.replace("/");

            } else if (data.board_full) {
                alert("The leaderboard is full. Unable to join.");

            } else if (data.user_added || data.user_removed) {

                // Refresh player list and button options on success.
                $(".leaderboard-stats").load(" .leaderboard-stats", function(){button.children().unwrap()});
                $(".leaderboard-table").load(" .leaderboard-table", function(){button.children().unwrap()});
                $(".leaderboard-buttons").load(" .leaderboard-buttons", function(){button.children().unwrap()});

            } else {
                alert("Unable to process request. There may not be free spaces left for this leaderboard.");
            }
        },
        error: function (rs, e) {
            alert('Sorry, there was an error.');
        }
    });
}