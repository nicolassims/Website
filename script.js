if (!localStorage.getItem('theme')) {//if the user hasn't set a theme before...
    setTheme('light');//set the light theme by default
} else {//otherwise...
    setTheme(theme);//set their previously-selected theme
}

let themeDots = document.getElementsByClassName("theme-dot");

for (var i = 0; i < themeDots.length; i++) {
    themeDots[i].addEventListener('click', function () {
        setTheme(this.dataset.mode);
    })
}

function setTheme(mode) {//sort this out. FIX THIS
    if (mode == 'light') {
        document.getElementById('theme-style').href = 'default.css';
    } else {
        document.getElementById('theme-style').href = 'styles/' + mode + '.css';
    }



    /*if (mode == 'dark') {
        document.getElementById('theme-style').href = 'styles/dark.css';
    } else if (mode == 'purple') {
        document.getElementById('theme-style').href = 'styles/purple.css';
    } else if (mode == 'green') {
        document.getElementById('theme-style').href = 'styles/green.css';
    }*/
    localStorage.setItem('theme', mode);
}