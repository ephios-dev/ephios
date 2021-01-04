$(document).ready(function () {
    const clipboard = new ClipboardJS(".clipboard-button");

    clipboard.on("success", function (e) {
        const btn = $("#calendar-copy-btn");
        btn.tooltip("show");
        setTimeout(function () {
            btn.tooltip("hide")
        }, 1000);
    });
});
