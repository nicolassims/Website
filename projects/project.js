let theme = localStorage.getItem('theme');//get the previously-stored theme, returning "Null" if none can be found.
if (!theme) {//if the user hasn't set a theme before...
    setTheme('light');//set the light theme by default
} else {//otherwise...
    setTheme(theme);//set their previously-selected theme
}

let pw = document.querySelector('.gallery-wrapper');//get the gallery-wrapper element, which is the parent of all the posts...
for (var i = pw.children.length; i >= 0; i--) {//look through every child in the post-wrapper, then...
    pw.appendChild(pw.children[Math.random() * i | 0]);//append that child in a new order.
}

setInterval(function () {
    var ele = document.getElementById('blinker');
    ele.style.visibility = (ele.style.visibility == 'hidden' ? '' : 'hidden');
}, 1000);

function setTheme(mode) {
    if (mode == 'light') {//if the mode was light...
        document.getElementById('theme-style').href = '../default.css';//then set the css style to the default
    } else {//otherwise...
        document.getElementById('theme-style').href = '../styles/' + mode + '.css';//assign the corresponding css style
    }
}

var imagelist = document.getElementsByClassName("gallery-image");
for (var i = 0; i < imagelist.length; i++) {
    imagelist[i].addEventListener('click', function () {
        var modal = document.getElementById("myModal");
        var modalImg = document.getElementById("modal-container");
        modal.style.display = "block";
        modalImg.src = this.src;
        modalImg.title = this.title;
    })
}

var modal = document.getElementById("myModal");
modal.addEventListener('click', function () {
    modal.style.display = "none";
})