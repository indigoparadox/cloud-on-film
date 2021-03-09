
(function( $ ) {

$.fn.enableTags = function( tagsURL ) {

    // Setup tags autocomplete.
    let tagNames = new Bloodhound( {
        datumTokenizer: function( d ) {
            var tokens = d.name.split( /[\s\/]+/ );
            //console.log( tokens );
            return tokens;
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        prefetch: {
            url: tagsURL,
            filter: function( list ) {
                return $.map( list, function( tagname ) {
                    return { name: tagname }; 
                } );
            }
        }
    } );
    
    tagNames.clearPrefetchCache();
    tagNames.initialize();
        
    $(this).tagsinput( {
        tagClass: function( name ) {
            return 'bg-dark';
        },
        typeaheadjs: {
            name: 'tagnames',
            displayKey: 'name',
            valueKey: 'name',
            source: tagNames.ttAdapter()
        }
    } );
}

}( jQuery ));
