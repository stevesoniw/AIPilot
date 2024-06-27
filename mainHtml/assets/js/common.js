var g_stockCodes;

//2024-06-24 추가
async function initStockCodeData(searchField, isEng=true)
{
    const $searchField = $("#" + searchField);

    $searchField.prop('disabled', true);

    $(".search-ipt-wrap .loader-small").show();       

    $searchField.attr("placeholder" , "종목 코드를 불러오는중입니다. 잠시만 기다려주세요...")

    let stockCodeUrl =  isEng === true ?  '/api/get_foreign_stock_symbols' : '/stock-codes/'              
    
    try
    {
        const response =  await fetch(stockCodeUrl, {
            method: 'GET',
            headers: {'Content-Type': 'application/json'}                                                
        });

        if (!response.ok) throw new Error('Network response was not ok.');

        const data = await response.json();                    

        data.sort((a, b) => {
            if (a.symbol < b.symbol) {
                return -1;
            }
            else if (a.symbol > b.symbol) {
                return 1;
            }else if (a.description < b.description) {
                return -1;
            }
            else if (a.description > b.description) {
                return 1;
            }


            return 0;
        });     
        
        if(isEng)
            g_stockCodes = data.map(stock => ({ id: stock.symbol, text: `${stock.symbol} (${stock.description})`, name: stock.description}))
        else
            g_stockCodes = data.map(stock => ({ id: stock[1], text: `${stock[0]} (${stock[1]})`, name:stock[0]}))
    
        $searchField.prop('disabled', false);
        $(".search-ipt-wrap .loader-small").hide();       

        $searchField.attr("placeholder" , "원하시는 종목을 검색해주세요.")

        if(!isEng){

            $("#downloadExcel").on("click", function(e){
                console.log("downloadExcelForStockCode>>>");
                downloadExcelForStockCode(false);
    
            });

        }

        

    } catch (error) {
        console.error('Error:', error);
        $searchField.prop('disabled', false);
        $searchField.focus();
    } 


}

//2024-06-24 추가
function initStockCodeSearch(searchField, stockCodeArea, isKorean = true, callback=null)
{                                              
    const $stockCodeAreas =  $("#" + stockCodeArea);              
    const $searchField = $("#" + searchField);

    const dislayMatchedCode = (input) =>{

        const filteredStocks = g_stockCodes.filter(stock => stock.text.toLowerCase().includes(input.toLowerCase()));                        

        if( filteredStocks.length > 0){
            $stockCodeAreas.show();
            $stockCodeAreas.scrollTop()
        }
        else{
            $stockCodeAreas.html("");
            $stockCodeAreas.hide();
        }

        filteredStocks.forEach(stock => {

            const div = document.createElement('div');
            div.classList.add('stock-code-area');
            div.textContent = stock.text;   

            div.dataset.stockCode = stock.id;                           

            div.addEventListener('click', () => {

                $searchField.val(stock.id);                     
                
            
                $stockCodeAreas.html("");
                $stockCodeAreas.hide();
                
                if(callback != null)
                    callback();

            });

            $stockCodeAreas.append($(div))        

            
        });

    };
    

    if(isKorean){      

        $searchField.on('keypress', function(e) { 

            if (e.key === 'Enter' && this.value.trim() !== '') {

                let term = $searchField.val();                    
            
                if (/[\u3131-\uD79D\uAC00-\uD7A3]/.test(term)) {

                    if (term.length >= 2) {

                        //let debounceTimer = setTimeout(function() {

                        $searchField.prop('disabled', true);

                        $(".search-ipt-wrap .loader-small").show();       

                        $searchField.val(term + " (종목 코드를 불러오는중입니다. 잠시만 기다려주세요...)"); 

                        getEngNameFromGoogle(term).then(stockCode => {                                      

                            if (stockCode) {                                                                                            


                                console.log(`dislayMetchedCode>>>${stockCode}`)                                             

                                $searchField.prop('disabled', false);
                                $searchField.focus();

                                $(".search-ipt-wrap .loader-small").hide();       

                                $searchField.val(term); 
                                
                                dislayMatchedCode(stockCode);     
                                
                                

                            }
                    
                        });

                        //}, 3000);
                    }
                }

            }
        });


    }


    $searchField.on('input', function(event) {
      
        
        const term = $(this).val();   
        
        if(isKorean){                    
        
            if (!/[\u3131-\uD79D\uAC00-\uD7A3]/.test(term)) {
                
                $stockCodeAreas.html("");                    

                if (term) {

                    dislayMatchedCode(term);                        
                }
                else{
                    $stockCodeAreas.html("");
                    $stockCodeAreas.hide();
                }

            }           

        
        }else{

            $stockCodeAreas.html("");                    

            if (term) {

                dislayMatchedCode(term);       
                
               
            }
            else{                
                $stockCodeAreas.hide();
            }

        }


    });


    
    $('div.search-ipt-wrap').keydown(function(event) {    

        if($stockCodeAreas.is(':visible')) {                            

            if (event.key === 'ArrowUp') {         
                
                //event.preventDefault(); 

                console.log('stockCodeAreas::ArrowUp>>>')

                let $items = $('div.stock-code-areas  div.stock-code-area');                     
                let $selectedItems = $('div.stock-code-areas  div.stock-code-area.selected');                

                if($selectedItems.length <= 0){              

                    $stockCodeAreas.hide();

                }else{

                    if($selectedItems.index() == 0 ){
                        $selectedItems = $items.last();

                        $items.removeClass('selected')
                        $selectedItems.addClass('selected')
                        
                    }
                    else{

                        $selectedItems = $selectedItems.prev();                      

                        $items.removeClass('selected')
                        $selectedItems.addClass('selected')                        

                    }

                }

                if($selectedItems.length > 0){    

                    $stockCodeAreas.scrollTop($selectedItems.offset().top - $stockCodeAreas.offset().top + $stockCodeAreas.scrollTop());
                }

                
            } else if (event.key === 'ArrowDown') {

               // event.preventDefault(); 

                console.log("stockCodeAreas::ArrowDown>>>")

                let $items = $('div.stock-code-areas  div.stock-code-area');                         
                let $selectedItems = $('div.stock-code-areas  div.stock-code-area.selected');                

                if($selectedItems.length <= 0){              
                    
                    $selectedItems = $items.eq(0);
                    $selectedItems.addClass('selected')

                }else{

                    if($selectedItems.index() == ($items.length - 1) ){
                        $selectedItems = $items.first();

                        $items.removeClass('selected')
                        $selectedItems.addClass('selected')
                        
                    }
                    else{

                        $selectedItems = $selectedItems.next();                      

                        $items.removeClass('selected')
                        $selectedItems.addClass('selected')                        

                    }

                }

                if($selectedItems.length > 0){    

                    $stockCodeAreas.scrollTop($selectedItems.offset().top - $stockCodeAreas.offset().top + $stockCodeAreas.scrollTop());
                }                                   
                            
            }else if (event.key === 'Enter') {

                //event.preventDefault(); 

                console.log("stockCodeAreas::Enter>>>")              

                let $selectedItems = $('div.stock-code-areas  div.stock-code-area.selected');                

                if($selectedItems.length > 0){
                    
                    console.log("selectedItems>>" + $selectedItems.data("stock-code"))  
                    
                    $('div.search-ipt-wrap input').val($selectedItems.data("stock-code"));                                                       
            
                    $stockCodeAreas.html("");
                    $stockCodeAreas.hide();

                    if(callback != null)
                        callback();

                }                
                
            }        
        }

    });


}










function ExcelDownLoad(dataArray, sheetName, headerNames, fileName)
{
    this.dataArray = dataArray;
    this.sheetName = sheetName;
    this.headerNames = headerNames;
    this.fileName = fileName;

    ExcelDownLoad.prototype.downloadExcel = function(){


        let table = this.convertToTable();

        let wb = XLSX.utils.table_to_book(table, {sheet:this.sheetName, raw:true});
    
        XLSX.writeFile(wb, (fileName + '.xlsx'));		
    };

    ExcelDownLoad.prototype.convertToTable = function(){
        
        let table = document.createElement("table");	

        let thead = table.createTHead();
        let headerRow = thead.insertRow();

        this.headerNames.forEach(headerName => {
            let headerCell;
            headerCell = document.createElement("th");
            headerCell.innerHTML = headerName;
            headerRow.appendChild(headerCell);			
        });					

        let tbody = table.createTBody();
        
        this.dataArray.forEach(data => {
            
            let tableRow = tbody.insertRow();				
            
            Object.keys(data).forEach(function(key){

                let tableCell = tableRow.insertCell();				                    

                tableCell.innerHTML = data[key];

            });		
            
            
        });	

        return table;			
    };

}

async function downloadExcelForStockCode(isEng=true)
{ 
    // let confirmYn = confirm("종목코드를 다운로드 하시겠습니까?");
    // if (!confirmYn) {
    //     return true;
    // }                               

    // const stockCodeUrl =  isEng === true ?  '/api/get_foreign_stock_symbols' : '/stock-codes/'              

    let stockCodes  = [];     
    
    try
    {
    //     const response =  await fetch(stockCodeUrl, {
    //         method: 'GET',
    //         headers: {'Content-Type': 'application/json'}                                                
    //     });

    //     if (!response.ok) throw new Error('Network response was not ok.');

    //     const data = await response.json();                    
       
    //     if(isEng)
    //         stockCodes = data.map(stock => ({ code: stock.symbol, name: stock.description }))
    //     else
    //         stockCodes = data.map(stock => ({ code: stock[1], name: stock[0] })) 

    //     stockCodes.sort((a, b) => {

    //         if(isEng){

    //             if (a.code < b.code) {
    //                 return -1;
    //             }
    //             else if (a.code > b.code) {
    //                 return 1;
    //             }else if (a.name < b.name) {
    //                 return -1;
    //             }
    //             else if (a.name > b.name) {
    //                 return 1;
    //             }
    //         }
    //         else{

    //             if (a.name < b.name) {
    //                 return -1;
    //             }
    //             else if (a.name > b.name) {
    //                 return 1;
    //             }else if (a.code < b.code) {
    //                 return -1;
    //             }
    //             else if (a.code > b.code) {
    //                 return 1;
    //             }

    //         }

    //         return 0;
    //     });  
        
        stockCodes = g_stockCodes.map(stock => ({ code: stock.id, name:stock.name}))       
        stockCodes.sort((a, b) => {

            if(isEng){

                if (a.code < b.code) {
                    return -1;
                }
                else if (a.code > b.code) {
                    return 1;
                }else if (a.name < b.name) {
                    return -1;
                }
                else if (a.name > b.name) {
                    return 1;
                }
            }
            else{

                if (a.name < b.name) {
                    return -1;
                }
                else if (a.name > b.name) {
                    return 1;
                }else if (a.code < b.code) {
                    return -1;
                }
                else if (a.code > b.code) {
                    return 1;
                }

            }

            return 0;
        });  

        const headerNames = ["코드","이름"];	
        const fileName  =  isEng === true ?  'aipilot_stock_codes_eng' : 'aipilot_stock_codes_kor' ;                        

        const excelDownLoad = new ExcelDownLoad(stockCodes, '종목코드',  headerNames  , `${fileName}_${Date.now()}`);
        excelDownLoad.downloadExcel();       
    
       
    } catch (error) {
        console.error('Error:', error);               
    }

}