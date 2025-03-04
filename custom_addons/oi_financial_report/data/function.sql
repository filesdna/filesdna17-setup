CREATE OR REPLACE FUNCTION public.translate(
	p_value jsonb,
	p_lang text
	)
    RETURNS text
    LANGUAGE 'plpgsql'
	IMMUTABLE 
AS $BODY$

    DECLARE
     res text;
    BEGIN
    
	    res := p_value->>p_lang::text;
		            
		if res is null or res='' then
			res := p_value->>'en_US'::text;
		end if;
		
		if res is null or res='' then
			res := p_value::text;
		end if;
		
        return res;
    
    END;
        
$BODY$;

CREATE OR REPLACE FUNCTION public.translate(
	p_text text,
	p_lang text
	)
    RETURNS text
    LANGUAGE 'plpgsql'
	IMMUTABLE 
AS $BODY$

    DECLARE
     res text;
	 p_value jsonb;
    BEGIN
	
		p_value := p_text::jsonb;
    
	    res := p_value->>p_lang;
		            
		if res is null or res='' then
			res := p_value->>'en_US';
		end if;
		
		if res is null or res='' then
			res := p_text;
		end if;
		
        return res;
    
    END;
        
$BODY$;

CREATE OR REPLACE FUNCTION en_to_ar(
	num text)
    RETURNS text
    LANGUAGE 'plpgsql'
	IMMUTABLE 
AS $BODY$

	BEGIN
	
		num := replace(num, '0', '٠');
		num := replace(num, '1', '١');
		num := replace(num, '2', '٢');
		num := replace(num, '3', '٣');
		num := replace(num, '4', '٤');
		num := replace(num, '5', '٥');
		num := replace(num, '6', '٦');
		num := replace(num, '7', '٧');
		num := replace(num, '8', '٨');
		num := replace(num, '9', '٩');
		
	    return num;
	
	END;
        

$BODY$;
