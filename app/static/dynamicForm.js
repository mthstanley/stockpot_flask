// dynamicForm.js

$(function(){

    var increment = function(string){
        return string.replace(new RegExp('-(\\d+)-', 'gi'), function(match, p1){
            return '-'+(parseInt(p1)+1)+'-';
        });
    };

    $('.add-field').on('click', function(e){
        e.preventDefault();
        var target = $($(e.currentTarget).data('target'));
        var clone = target.children().last().clone();
        $(clone).find('.dynamic-field').addBack().each(function(index, elt){
            elt.id = increment(elt.id);
            if (elt.name){
                elt.name = increment(elt.name);
            }
            // reset input elements
            if($(elt).is('input')){
                // csrf token have type hidden and we don't want to reset them
                if(elt.type !== 'hidden'){
                    $(elt).val('');
                }
            }
            if($(elt).is('select')){
                $(elt).children().removeAttr('selected');
            }
            if($(elt).is('textarea')){
                $(elt).val('');
            }
        });
        target.append(clone);
    });

    $(document).on('click', '[id$=remove]',function(e){
        e.preventDefault();
        var idPrefix = e.currentTarget.id.split('-').slice(0,2).join('-');
        var toRemove = $('#' + idPrefix + '-group');
        // make sure user can't remove all input groups
        if(toRemove.siblings().length){
            toRemove.remove();
        }
    });


    var previewImage = function(input, display, defaultImg) {
    
        if (input.files && input.files[0]){
            var reader= new FileReader();

            reader.onload = function(e){
                display.attr('src', e.target.result);
            }

            reader.readAsDataURL(input.files[0]);
        }else{
            display.attr('src', defaultImg);
        }
    }

    var recipeImg = $('img#upload-img').attr('src');
    $('input#image').on('change', function(){
        previewImage(this, $('img#upload-img'), recipeImg);
    });
});
