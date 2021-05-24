let theme = localStorage.getItem('theme');//get the previously-stored theme, returning "Null" if none can be found.
if (!theme) {//if the user hasn't set a theme before...
    setTheme('light');//set the light theme by default
} else {//otherwise...
    setTheme(theme);//set their previously-selected theme
}

let themeDots = document.getElementsByClassName("theme-dot");//get all the theme-switching dot options
for (var i = 0; i < themeDots.length; i++) {//for each 'dot that was got'...
    themeDots[i].addEventListener('click', function() {//assign an event to trigger when clicked
        setTheme(this.dataset.mode);//and set the theme to the mode that was set in the index.html
    })
}

function setTheme(mode) {
    if (mode == 'light') {//if the mode was light...
        document.getElementById('theme-style').href = 'default.css';//then set the css style to the default
    } else {//otherwise...
        document.getElementById('theme-style').href = 'styles/' + mode + '.css';//assign the corresponding css style
    }
    localStorage.setItem('theme', mode);//and set that css style for future visits.
}

var pw = document.querySelector('.post-wrapper');//get the post-wrapper element, which is the parent of all the posts...
for (var i = pw.children.length; i >= 0; i--) {//look through every child in the post-wrapper, then...
    pw.appendChild(pw.children[Math.random() * i | 0]);//append that child in a new order.
}