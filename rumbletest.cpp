#include <iostream>
#include <SDL.h>

int main(){
	SDL_Init(SDL_INIT_EVERYTHING);
	SDL_Haptic*  haptic = NULL;
	if (-1 == SDL_GameControllerAddMappingsFromFile("gamecontrollerdb.txt"))
		printf( "Warning: %s\n", SDL_GetError() );
	int controller_amount = SDL_NumJoysticks();
	for(int i = 0; i < controller_amount; i++){
		SDL_Joystick* js = SDL_JoystickOpen(i);
		if (js) {
			SDL_JoystickGUID guid = SDL_JoystickGetGUID(js);
			char guid_str[1024];
			SDL_JoystickGetGUIDString(guid, guid_str, sizeof(guid_str));
			const char* name = SDL_JoystickName(js);
			printf("%s \"%s\" \n", guid_str, name);
			// SDL_JoystickClose(js);
		
			// SDL_GameController* controller = SDL_GameControllerOpen(i);
			// if( controller == NULL ) {
			//	printf( "Warning: Unable to open game controller! SDL Error: %s\n", SDL_GetError() );
			// }
			
			// SDL_Joystick* joystick = SDL_GameControllerGetJoystick(controller);
			printf("Opened joystick: %s\n", SDL_JoystickName(js));
			//Get controller haptic device
			haptic  = SDL_HapticOpenFromJoystick( js );
			if( haptic == NULL ) {
				printf( "Warning: Controller does not support haptics! SDL Error: %s\n", SDL_GetError() );
			}
			else {
				//Get initialize rumble
				if( SDL_HapticRumbleInit( haptic ) < 0 ) {
					printf( "Warning: Unable to initialize rumble! SDL Error: %s\n", SDL_GetError() );
				}
				else{ //Got Rumble and it is initialized
					 SDL_HapticRumblePlay( haptic, 0.75,500 ); //Play at 75% for 500 ms
				}
			}
			
			SDL_JoystickClose(js);
		}
		//Wait a bit so not all controllers rumble at the same time
		SDL_Delay(1000);
	   
		// SDL_GameControllerClose(controller);
		// No need to close the joystick, the close game controller should handle that
		if(haptic)
			SDL_HapticClose( haptic );
	}
	
	return 0;
};
