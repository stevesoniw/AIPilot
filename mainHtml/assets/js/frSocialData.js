    /* 팝업 시작 */
    $('#aiSummary').dialog({
        dialogClass : 'research-dialog',
        title : '',
        modal : true,
        draggable : false,
        resizable : false,
        autoOpen: false,
        width: 700,
        height: 500,
        open : function(){
            $('.ui-widget-overlay').on('click', function(){
                $('#aiSummary').dialog('close');
            });
        }
    });

    $('.ai-summary-pop').click(function(){
        alert("11");
        $('#aiSummary').dialog('open');
    });
    /* 팝업 끝 */