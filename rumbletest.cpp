#include <iostream>
#include <SDL.h>

int main(){
	SDL_Init(SDL_INIT_EVERYTHING);
	SDL_Haptic*  haptic = NULL;
	// if (-1 == SDL_GameControllerAddMappingsFromFile("gamecontrollerdb.txt"))
	// 	printf( "Warning: %s\n", SDL_GetError() );
	int controller_amount = SDL_NumJoysticks();
	printf("controller_amount = %d\n", controller_amount);
	for(int i = 0; i < controller_amount; i++){
		SDL_Joystick* js = SDL_JoystickOpen(i);
		if (js) {
			SDL_JoystickGUID guid = SDL_JoystickGetGUID(js);
			char guid_str[1024];
			SDL_JoystickGetGUIDString(guid, guid_str, sizeof(guid_str));
			const char* name = SDL_JoystickName(js);
			printf("%s \"%s\" \n", guid_str, name);
			printf("Opened joystick: %s\n", SDL_JoystickName(js));
			
			//Get controller haptic device
			haptic  = SDL_HapticOpenFromJoystick( js );
			if( haptic == NULL ) {
				printf( "Warning: Controller does not support haptics! SDL Error: %s\n", SDL_GetError() );
			} else {
				//Get initialize rumble
				if( SDL_HapticRumbleInit( haptic ) < 0 ) {
					printf( "Warning: Unable to initialize rumble! SDL Error: %s\n", SDL_GetError() );
				}
				else{ //Got Rumble and it is initialized
					 SDL_HapticRumblePlay( haptic, 0.75,500 ); //Play at 75% for 500 ms
				}
			}
			SDL_JoystickClose(js);
		} else {
			printf( "Warning: %s\n", SDL_GetError() );
		}
		// SDL_GameControllerClose(controller);
		// No need to close the joystick, the close game controller should handle that
		if(haptic)
			SDL_HapticClose( haptic );
	}
	
	return 0;
};
