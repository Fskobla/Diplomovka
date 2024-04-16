var inputWord = document.getElementById('search_word');
var searchCloseButton = document.getElementById('search-close')
var searchIconButton = document.getElementById('search-icon-button')
var searchIconOptions = document.getElementById('search-icon-options')
var searchOptions = document.querySelector('.search-bar-options')

inputWord.addEventListener('input', function (){
   if(inputWord.value.trim() !== ''){
       searchCloseButton.style.visibility = 'visible';
   } else{
       searchCloseButton.style.visibility = "hidden";
   }
});

searchCloseButton.addEventListener('click', function (){
    inputWord.value = '';
    searchCloseButton.style.visibility = "hidden";
});

searchIconButton.addEventListener('click', function() {
        document.querySelector('#searchForm').submit();
});

searchIconOptions.addEventListener('click', function (){
    if(searchOptions.style.visibility === 'hidden'){
        searchOptions.style.visibility = 'visible';
        searchIconOptions.textContent = 'expand_less'
    }else{
        searchOptions.style.visibility = 'hidden';
        searchIconOptions.textContent = 'expand_more'
    }
});
