/// DESCRIPTION icon
const descriptionContainers = document.querySelectorAll('.description-container');
descriptionContainers.forEach(container => {
    container.addEventListener('click', () => {
        const content = container.querySelector('.description-content');
        if (content.classList.contains('show')) {
            content.classList.remove('show');
            content.classList.add('hide');
        } else {
            content.classList.remove('hide');
            content.classList.add('show');
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
        updatePlaceholder(text);
        filterCards();
    });

    $("#search-icon-button-dropdown").click(function () {
        filterCards();
    });
    $(".search-input-dropdown").keypress(function(event) {
        if (event.which === 13) {
            filterCards();
        }
    });
});

function updatePlaceholder(text){
    var placeholderText = "Enter ";
    switch(text.toLowerCase()) {
        case 'title':
            placeholderText += "title";
            break;
        case 'author':
            placeholderText += "author";
            break;
        case 'keyword':
            placeholderText += "keyword";
            break;
        case 'year':
            placeholderText += "year";
            break;
        default:
            placeholderText += "word";
    }
    $(".search-input-dropdown").attr("placeholder", placeholderText);
}


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
                case 'year':
                    isVisible = card.querySelector(".date").innerText.toUpperCase().indexOf(filter) > -1;
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
/// SEARCH ICON CLOSE
var searchCloseButton = document.getElementById('close-icon-button-dropdown');
var inputWordOption = document.getElementById('search_option');

inputWordOption.addEventListener('input', function (){
   if(inputWordOption.value.trim() !== ''){
       searchCloseButton.style.visibility = 'visible';
   } else{
       searchCloseButton.style.visibility = "hidden";
   }
});

searchCloseButton.addEventListener('click', function (){
    inputWordOption.value = '';
    searchCloseButton.style.visibility = "hidden";
});

/// SORT ICONS
document.getElementById('sortAsc').addEventListener('click', sortAsc);
document.getElementById('sortDesc').addEventListener('click', sortDesc);

function sortAsc() {
    const cardsContainer = document.querySelector('.card-container');
    const cards = Array.from(cardsContainer.querySelectorAll('.card'));
    cards.sort((a, b) => {
        const titleA = a.querySelector('.article-title').innerText.toLowerCase();
        const titleB = b.querySelector('.article-title').innerText.toLowerCase();
        return titleA.localeCompare(titleB);
    });
    renderCards(cards);
}

function sortDesc() {
    const cardsContainer = document.querySelector('.card-container');
    const cards = Array.from(cardsContainer.querySelectorAll('.card'));
    cards.sort((a, b) => {
        const titleA = a.querySelector('.article-title').innerText.toLowerCase();
        const titleB = b.querySelector('.article-title').innerText.toLowerCase();
        return titleB.localeCompare(titleA);
    });
    renderCards(cards);
}

function renderCards(cards) {
    const cardsContainer = document.querySelector('.card-container');
    cards.forEach(card => {
        cardsContainer.appendChild(card);
    });
}

/// DOWNLOAD ICON
document.getElementById('download-icon').addEventListener('click', function() {
    // Get the data from the HTML
    const links = [];
    document.querySelectorAll('.card').forEach(card => {
        const linkData = {
            article_title: card.querySelector('.article-title').innerText,
            link: card.querySelector('.article-link').getAttribute('href'),
            date: card.querySelector('.date').innerText,
            authors: Array.from(card.querySelectorAll('.author-item')).map(author => author.innerText),
            description: card.querySelector('.description-content').innerText,
            keywords: Array.from(card.querySelectorAll('.keyword-item')).map(keyword => keyword.innerText),
            citations: Array.from(card.querySelectorAll('.citation-item')).map(citation => citation.innerText)
        };
        links.push(linkData);
    });

    // Convert the data to JSON
    const jsonData = JSON.stringify(links, null, 2);

    // Create a blob with the JSON data
    const blob = new Blob([jsonData], { type: 'application/json' });

    // Create a link element and trigger the download
    const a = document.createElement('a');
    const url = URL.createObjectURL(blob);
    a.href = url;
    a.download = 'articles.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});