/// DESCRIPTION icon
const descriptionContainers = document.querySelectorAll('.description-container');
descriptionContainers.forEach(container => {
    container.addEventListener('click', () => {
        const content = container.querySelector('.description-content');
        if (content.style.display === 'none' || content.style.display === '') {
            content.style.display = 'block';
            content.style.transition = 'ease-in 0.5s';
        } else {
            content.style.display = 'none';
            content.style.transition = 'ease-out 0.5s';
        }
    });
});

/// KEYWORD icon
const keywordContainers = document.querySelectorAll('.keywords-container');

keywordContainers.forEach(container => {
    container.addEventListener('click', () => {
        const keywordsList = container.querySelector('.keywords-list');
        keywordsList.classList.toggle('show');
    });
});


/// CITATION icon
const citationContainers = document.querySelectorAll('.citations-container');

citationContainers.forEach(container => {
    container.addEventListener('click', () => {
        const citationsList = container.querySelector('.citations-list');
        citationsList.classList.toggle('show');
    });
});


/// SEARCH BAR with keyword, title, author options
$(document).ready(function(){
    $(".default-option-selected").click(function(){
        $(".selected-value-dropdown").addClass("active");
    });

    $(".selected-value-dropdown li").click(function(){
        var text = $(this).text();
        $(".default-option-selected").text(text);
        $(".selected-value-dropdown").removeClass("active");
    });
    $("#search-icon-button-dropdown").click(function () {
        filterCards();
    });
});

function filterCards() {
    var input, filter, cards, card, i;
    input = document.querySelector(".search-input-dropdown");
    filter = input.value.toUpperCase();
    cards = document.querySelectorAll(".card");
    var selectedOption = $(".default-option-selected").text().toLowerCase();
    var totalResults = 0;
    for (i = 0; i < cards.length; i++) {
        card = cards[i];
        var isVisible = false;
        switch(selectedOption) {
            case 'title':
                isVisible = card.querySelector(".article-title").innerText.toUpperCase().indexOf(filter) > -1;
                break;
                case 'author':
                    isVisible = card.querySelector(".author-item").innerText.toUpperCase().indexOf(filter) > -1;
                    break;
                    case 'keyword':
                        var keywords = card.querySelectorAll(".keyword-item");
                    keywords.forEach(function(keyword) {
                        if (keyword.innerText.toUpperCase().indexOf(filter) > -1) {
                            isVisible = true;
                        }
                    });
                    break;
                default:
                    isVisible = true;
            }
            if (isVisible) {
                card.style.display = "";
                totalResults++;
            } else {
                card.style.display = "none";
            }
        }
        $(".total-results").text("Total results: " + totalResults);
    }

