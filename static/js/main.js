// Test script. Changes colours of links ('<a>' tags) when hovered over. Will be done in CSS normally.

/* Wait for the HTML document to load before firing the script.
   Equivalent jQuery: $(document).ready() */
document.addEventListener("DOMContentLoaded", function() {
	// Get all the anchors in the HTML document - all '<a>' tags. Equivalent jQuery: $("a")
	var anchors = document.getElementsByTagName("a");

	// Loop through the anchors and add event-listeners to each
	for (let i = 0; i < anchors.length; i++) {

		// Add mouseover and mouseout events to each anchor. Change colour if event occurs. 'e' param is the event object
		anchors[i].addEventListener("mouseover", function(e) {
			e.target.style.color = "blue";
		});
		anchors[i].addEventListener("mouseout", function(e) {
			e.target.style.color = "red";
		});
	}
});