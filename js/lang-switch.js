document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("a[data-md-component='i18n-selector']").forEach(function (el) {
        el.addEventListener("click", function (event) {
            event.preventDefault();
            
            const newLang = el.getAttribute("href").replace("/", "");
            const currentPath = window.location.pathname.split("/").slice(2).join("/");

            window.location.href = `/${newLang}/${currentPath}`;
        });
    });
});
