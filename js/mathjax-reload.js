document.addEventListener("DOMContentLoaded", function () {
    function reloadMathJax() {
        if (window.MathJax) {
            MathJax.typesetPromise(); // `typesetClear()` は削除し、再描画のみ
        }
    }

    // 言語切り替え時のページ変更を監視
    const observer = new MutationObserver(function () {
        reloadMathJax();
    });

    // コンテンツエリアを監視（MkDocs のメインコンテンツ部分）
    const contentArea = document.querySelector("main");
    if (contentArea) {
        observer.observe(contentArea, { childList: true, subtree: true });
    }
});
