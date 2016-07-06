define([
    "filters",
    "jquery",
    "config.datatables",
    "hq.helpers",
], function(
    filters,
    $,
    datatablesConfig
) {
    "use strict";
    filters.init();
    var initialPageData = $.parseJSON($("#initial-page-data").text());
    if (initialPageData.renderReportTables) {
        var reportTables = new datatablesConfig.HQReportDataTables(initialPageData.reportTablesOptions);
        if (typeof standardHQReport !== 'undefined') {
            standardHQReport.handleTabularReportCookies(reportTables);
        }
        reportTables.render();
    }

    $('.header-popover').popover({
        trigger: 'hover',
        placement: 'bottom'
    });
});
