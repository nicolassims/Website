let theme = localStorage.getItem('theme');//get the previously-stored theme, returning "Null" if none can be found.
if (!theme) {//if the user hasn't set a theme before...
    setTheme('light');//set the light theme by default
} else {//otherwise...
    setTheme(theme);//set their previously-selected theme
}

var imagelist = document.getElementsByClassName("gallery-image");
for (var i = 0; i < imagelist.length; i++) {
    imagelist[i].addEventListener('click', function () {
        if (!this.classList.contains("enlarged")) {
            shrinkAll();
            this.classList.add("enlarged");
        } else {
            shrinkAll();
        }
    })
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

function shrinkAll() {
    imagelist = document.getElementsByClassName("gallery-image");
    for (var i = 0; i < imagelist.length; i++) {
        imagelist[i].classList.remove("enlarged");
    }
}