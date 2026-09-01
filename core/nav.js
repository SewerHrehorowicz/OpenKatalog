(function () {
    const nav = document.getElementById('ok-nav');
    const toggle = document.getElementById('ok-nav-toggle');
    const list = document.getElementById('ok-nav-list');

    toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        nav.classList.toggle('open');
    });

    document.addEventListener('click', function (e) {
        if (!nav.contains(e.target)) {
            nav.classList.remove('open');
        }
    });

    function getPageTitle(page) {
        const heading = page.querySelector('h1, h2, h3, h4, h5, h6');
        if (heading) {
            return heading.textContent.trim();
        }
        return '';
    }

    function getPageNum(index) {
        if (typeof OK_PAGES !== 'undefined' && OK_PAGES[index] != null) {
            return OK_PAGES[index];
        }
        return '';
    }

    function buildNav() {
        list.innerHTML = '';
        const pages = document.querySelectorAll('.page');
        pages.forEach(function (page, i) {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = '#';
            const num = i + 1;
            const title = getPageTitle(page);
            const pageNum = getPageNum(i);
            let label = num + ': ';
            if (title) {
                label += title;
            }
            if (pageNum) {
                label += ' (' + pageNum + ')';
            }
            if (!title && !pageNum) {
                label += 'Page ' + num;
            }
            a.textContent = label;
            a.addEventListener('click', function (e) {
                e.preventDefault();
                page.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
            li.appendChild(a);
            list.appendChild(li);
        });
    }

    function highlightCurrent() {
        const pages = document.querySelectorAll('.page');
        const links = list.querySelectorAll('a');
        const scrollPos = window.scrollY + window.innerHeight / 3;
        let currentIdx = 0;
        pages.forEach(function (page, i) {
            if (page.offsetTop <= scrollPos) {
                currentIdx = i;
            }
        });
        links.forEach(function (link, i) {
            link.classList.toggle('active', i === currentIdx);
        });
    }

    buildNav();
    window.addEventListener('scroll', highlightCurrent, { passive: true });
    highlightCurrent();
})();
